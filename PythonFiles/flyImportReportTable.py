import bz2
import os
import sys
import queue
import threading
from csv import DictReader
import mysql.connector
from datetime import datetime, timedelta
from clickhouse_driver import Client
import time
from functools import wraps
import maidenhead as mh
from concurrent.futures import ThreadPoolExecutor, as_completed

def benchmark(method):
    @wraps(method)
    def timed(*args, **kw):
        ts = time.monotonic()
        result = method(*args, **kw)
        te = time.monotonic()
        s = (te - ts)
        # all_args = ', '.join(tuple(f'{a!r}' for a in args) + tuple(f'{k}={v!r}' for k, v in kw.items()))
        # print(f'{method.__name__}({all_args}): {s:2.3f} sec.')
        print(f'{method.__name__}: {s:2.3f} sec.')
        return result
    return timed


workDir = os.path.dirname(os.path.realpath(__file__))


class Progress:
    """
    Time-throttled progress printer for long-running pipeline steps.
    Each printed line is self-contained and prefixed with a label, so
    output from concurrent threads stays readable when lines interleave.
    """

    def __init__(self, label: str, total: int = 0, interval: float = 2.0):
        self.label     = label
        self.total     = total
        self.count     = 0
        self._start    = time.monotonic()
        self._last     = 0.0
        self._interval = interval

    def update(self, n: int = 1):
        self.count += n

    @property
    def _elapsed(self) -> float:
        return time.monotonic() - self._start

    @property
    def _rate(self) -> float:
        e = self._elapsed
        return self.count / e if e > 0 else 0.0

    def tick(self, extra: str = '', force: bool = False):
        now = time.monotonic()
        if not force and (now - self._last) < self._interval:
            return
        self._last = now
        self._print(extra)

    def _print(self, extra: str = ''):
        rate = self._rate
        if self.total > 0:
            pct   = self.count / self.total
            bw    = 28
            bar   = '█' * int(bw * pct) + '░' * (bw - int(bw * pct))
            eta_s = str(timedelta(seconds=int((self.total - self.count) / rate))) if rate > 0 else '?'
            print(f"  {self.label}  [{bar}] {pct*100:5.1f}%  "
                  f"{self.count:,}/{self.total:,}  {rate:,.0f}/s  ETA {eta_s}{extra}")
        else:
            elapsed_s = str(timedelta(seconds=int(self._elapsed)))
            print(f"  {self.label}  {self.count:,}  {rate:,.0f}/s  elapsed {elapsed_s}{extra}")

    def finish(self, extra: str = ''):
        elapsed_s = str(timedelta(seconds=int(self._elapsed)))
        rate      = self._rate
        if self.total > 0:
            print(f"  {self.label}  done: {self.count:,}/{self.total:,} in {elapsed_s}  ({rate:,.0f}/s){extra}")
        else:
            print(f"  {self.label}  done: {self.count:,} in {elapsed_s}  ({rate:,.0f}/s){extra}")


@benchmark
def decompressAndAlterReportFile(reportSuffix, dicZones):
    report_bz2_path = f"f:/PskReporterDATA/report-{reportSuffix}.sql.bz2"
    print(f"Start decompressing file: {report_bz2_path}")

    spots_path = f"C:/Users/qmax_/PSKReporterLocal/spots-sum-grid-ll-{reportSuffix}.csv"
    spots_path = spots_path.replace("\\", "/")
    spot_count = 0
    strPrefix = "INSERT INTO `report` VALUES ("
    # out_file_header = "spotId,utc,band,zone1,zone2\n"
    # out_file_header = "utc,band,zone1,zone2,dxcc1,dxcc2\n"
    # out_file_header = "utc,band,zone1,zone2,cnt\n"
    out_file_header = "utc,band,zone1,zone2,grid1,grid2,lat1,lon1,lat2,lon2,cnt,snr\n"
    bunchsize = 1912000  # Experiment with different sizes
    bunch = []

    # if altered report file not exists - will make it
    if not os.path.exists(spots_path):
        file_size = os.path.getsize(report_bz2_path)
        progress = Progress(f"[{reportSuffix}] bz2→csv")
        print(f"[{reportSuffix}] Decompressing {file_size / 1024**2:.1f} MB  →  {spots_path}")

        # Wrap bz2 around a plain file object so raw_fp.tell() tracks
        # compressed bytes read — gives accurate file-level percentage.
        with open(report_bz2_path, 'rb') as raw_fp:
            with bz2.BZ2File(raw_fp) as in_file:
                with open(spots_path, 'w', newline='') as out_file:
                    out_file.write(out_file_header)
                    for line in in_file:
                        line = line.decode()
                        if line.startswith(strPrefix):
                            line = line[len(strPrefix):-3]
                            for record in line.split('),('):
                                fields = record.split(',')
                                if fields[4] == '\'FT8\'':
                                    zone1 = dicZones.get(int(f'{fields[1]}'), 0)
                                    zone2 = dicZones.get(int(f'{fields[2]}'), 0)

                                    if zone1 != 0 and zone2 != 0 and zone1 != zone2:
                                        grid1 = str(zone1[1])
                                        grid2 = str(zone2[1])
                                        lat1, lon1 = mh.to_location(grid1)
                                        lat2, lon2 = mh.to_location(grid2)

                                        snr_raw = fields[7]
                                        snr = int(snr_raw) if snr_raw != 'NULL' else 0

                                        spot = fields[9] + "," + fields[14][1:-1] + "," + str(zone1[0]) + "," + str(zone2[0]) + "," + grid1 + "," + grid2 + "," + str(lat1) + "," + str(lon1) + "," + str(lat2) + "," + str(lon2) + ",1," + str(snr) + "\n"
                                        bunch.append(spot)
                                        spot_count += 1
                                        progress.update()

                                        if len(bunch) == bunchsize:
                                            out_file.writelines(bunch)
                                            bunch = []

                            # Tick once per INSERT statement (thousands of records each);
                            # bz2 reads in ~900 KB blocks so raw_fp.tell() updates coarsely
                            # but is accurate enough for a progress indicator.
                            pct_bz2 = raw_fp.tell() / file_size * 100
                            progress.tick(extra=f"  (file: {pct_bz2:.1f}%)")

                    out_file.writelines(bunch)

        progress.finish(extra=f"  →  {spots_path}")
        return spots_path
    else:
        print(f"[{reportSuffix}] CSV already exists, skipping decompression.")
        return spots_path


# def loadAltReportCsvFile(reportSuffix, csvFilePath):
#     #here we create a reduced report table and run csv file import
#     connection = connectToDB('main')
#     cursor = connection.cursor(dictionary=True, prepared=False)
#
#     table_drop_sql_str = (
#         "DROP TABLE IF EXISTS main.`report_reduced_"+reportSuffix+"`; "
#                           )
#
#     table_create_sql_str = (
#         "CREATE TABLE main.`report_reduced_"+reportSuffix+"` ("
#         "  `spotId` bigint NOT NULL,"
#         "  `utc` int NOT NULL,"
#         "  `band` varchar(10) NOT NULL,"
#         "  `idzone_1` int NOT NULL, "
#         "  `idzone_2` int NOT NULL, "
#         "  PRIMARY KEY (`spotId`), "
#         "  KEY `zoneband` (`idzone_1`,`idzone_2`,`band`),"
#         "  KEY `utczones` (`utc`,`idzone_2`,`idzone_1`)"
#         ") ENGINE=InnoDB;"
#     )
#
#     load_sql_str = (f"LOAD DATA INFILE \"{csvFilePath}\""
#                     " INTO TABLE main.`report_reduced_"+reportSuffix+"` "
#                     " FIELDS TERMINATED BY ',' "
#                     " ENCLOSED BY '\"' "
#                     " LINES TERMINATED BY '\n'"
#                     " IGNORE 1 ROWS")
#
#     cursor.execute(table_drop_sql_str)
#     cursor.execute(table_create_sql_str)
#     cursor.execute(load_sql_str)
#
#     print("Load csv complete. Row count: " + str(cursor.rowcount))
#
#     connection.commit()
#
#     cursor.close()
#     connection.close()


def determineUTCminMax(reportSuffix, clickhouseClient):
    utcMin = 0
    utcMax = 0
    tableSuffix = reportSuffix[:7].replace("-", "_")
    result = clickhouseClient.execute(f'SELECT min(utc) AS minUTC, max(utc) AS maxUTC FROM spots_{tableSuffix}')
    
    if result and len(result[0]) == 2:
        utcMin = datetime.utcfromtimestamp(result[0][0])
        utcMax = datetime.utcfromtimestamp(result[0][1])
    
#     report_csv_path = f"{workDir}/spots-{reportSuffix}.csv"
#     utcMax = 0
#     utcMin = sys.maxsize
#     with open(report_csv_path, mode='r') as in_file:
#         for line in in_file:
#             if (utcMax == 0):
#                 utcMax = 1
#                 continue
#             utc = int(line.split(",")[0])
#             if (utc > utcMax):
#                 utcMax = utc
#             if (utc < utcMin):
#                 utcMin = utc
    print(f"UTC from table spots_{tableSuffix}, min: {utcMin}, max: {utcMax}")
    return utcMin, utcMax


def count_csv_rows(path: str) -> int:
    """Fast data-row count for large CSV files. Reads in 4 MB chunks, excludes header."""
    count = 0
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            count += chunk.count(b'\n')
    return max(0, count - 1)


def ensure_table_snr_column(table_name, clickhouseClient):
    """Add snr Int32 column to existing tables that predate the SNR change."""
    columns = clickhouseClient.execute(
        f"SELECT name FROM system.columns WHERE database='default' AND table='{table_name}'"
    )
    existing = {row[0] for row in columns}
    if 'snr' not in existing:
        clickhouseClient.execute(f'ALTER TABLE default.`{table_name}` ADD COLUMN `snr` Int32 DEFAULT 0')
        print(f"Added snr column to {table_name}")
    if 'cnt' in existing:
        col_type = clickhouseClient.execute(
            f"SELECT type FROM system.columns WHERE database='default' AND table='{table_name}' AND name='cnt'"
        )
        if col_type and col_type[0][0] == 'UInt8':
            clickhouseClient.execute(f'ALTER TABLE default.`{table_name}` MODIFY COLUMN `cnt` UInt32')
            print(f"Upgraded cnt UInt8→UInt32 in {table_name}")


def _decompress_to_queue(reportSuffix: str, q: queue.Queue, batch_size: int, csv_path: str):
    """
    Producer: decompress bz2 → parse FT8 rows → push typed batches to q.
    Also writes csv_path as a checkpoint so the file can be re-uploaded without
    re-decompressing if ClickHouse upload fails later.
    Sentinel: q.put(None) on success; q.put(exc) on any error.
    """
    report_bz2_path = f"D:/PSKReporterDATA/report-{reportSuffix}.sql.bz2"
    strPrefix = "INSERT INTO `report` VALUES ("
    file_size = os.path.getsize(report_bz2_path)
    progress  = Progress(f"[{reportSuffix}] bz2")
    print(f"[{reportSuffix}] Decompressing {file_size / 1024**2:.1f} MB  →  {csv_path}")

    try:
        batch_rows: list = []
        csv_lines:  list = []

        with open(report_bz2_path, 'rb') as raw_fp, \
             bz2.BZ2File(raw_fp) as in_file, \
             open(csv_path, 'w', newline='') as csv_fp:

            csv_fp.write("utc,band,zone1,zone2,grid1,grid2,lat1,lon1,lat2,lon2,cnt,snr\n")

            for line in in_file:
                line = line.decode()
                if not line.startswith(strPrefix):
                    continue

                for record in line[len(strPrefix):-3].split('),('):
                    fields = record.split(',')
                    if fields[4] != "'FT8'":
                        continue

                    zone1 = dicZones.get(int(fields[1]), 0)
                    zone2 = dicZones.get(int(fields[2]), 0)
                    if zone1 == 0 or zone2 == 0 or zone1 == zone2:
                        continue

                    grid1 = str(zone1[1])
                    grid2 = str(zone2[1])
                    lat1, lon1 = mh.to_location(grid1)
                    lat2, lon2 = mh.to_location(grid2)
                    snr  = int(fields[7]) if fields[7] != 'NULL' else 0
                    utc  = int(fields[9])
                    band = fields[14][1:-1]

                    batch_rows.append({
                        'utc': utc, 'band': band,
                        'zone1': int(zone1[0]), 'zone2': int(zone2[0]),
                        'grid1': grid1, 'grid2': grid2,
                        'lat1': lat1, 'lon1': lon1, 'lat2': lat2, 'lon2': lon2,
                        'cnt': 1, 'snr': snr,
                    })
                    csv_lines.append(
                        f"{utc},{band},{zone1[0]},{zone2[0]},{grid1},{grid2},"
                        f"{lat1},{lon1},{lat2},{lon2},1,{snr}\n"
                    )
                    progress.update()

                    if len(batch_rows) == batch_size:
                        csv_fp.writelines(csv_lines)
                        q.put(batch_rows)       # blocks if consumer is behind (backpressure)
                        batch_rows = []
                        csv_lines  = []

                pct = raw_fp.tell() / file_size * 100
                progress.tick(extra=f"  (file: {pct:.1f}%)")

            if batch_rows:
                csv_fp.writelines(csv_lines)
                q.put(batch_rows)

        progress.finish()
        q.put(None)     # sentinel: decompress done

    except Exception as exc:
        q.put(exc)      # propagate error to consumer


@benchmark
def process_report_dump_file(reportSuffix, clickhouseClient):
    if not clickhouseClient:
        print("No valid Clickhouse client")
        return

    out_file_name = f'D:/PSKReporter-temp/spots-sum-grid-ll-{reportSuffix}.csv'
    tableSuffix   = reportSuffix[:7].replace('-', '_')
    table_name    = f'spots_sum_grid_ll_{tableSuffix}'
    batch_size    = 500_000

    clickhouseClient.execute(
        f'CREATE TABLE IF NOT EXISTS default.{table_name}'
        '(`utc` Int32, `band` String, `zone1` Int32, `zone2` Int32, '
        '`grid1` String, `grid2` String, '
        '`lat1` Float64, `lon1` Float64, `lat2` Float64, `lon2` Float64, '
        '`cnt` UInt32, `snr` Int32) '
        'ENGINE = SummingMergeTree '
        'ORDER BY (utc, band, zone1, zone2, grid1, grid2, lat1, lon1, lat2, lon2) '
        'PARTITION BY toYYYYMMDD(toDateTime(utc)) '
        'PRIMARY KEY (utc, band, zone1, zone2, grid1, grid2, lat1, lon1, lat2, lon2);'
    )
    ensure_table_snr_column(table_name, clickhouseClient)

    def _consume_queue(q: queue.Queue):
        """Consumer: read batches from q, insert into ClickHouse."""
        progress = Progress(f"[{reportSuffix}] →CH")
        chunk = 0
        while True:
            item = q.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            chunk += 1
            clickhouseClient.execute(f'INSERT INTO default.{table_name} VALUES', item)
            progress.update(len(item))
            progress.tick(extra=f"  chunk {chunk}", force=True)
        progress.finish()

    if os.path.isfile(out_file_name):
        # CSV checkpoint exists — skip decompression, upload straight from file
        print(f"[{reportSuffix}] CSV checkpoint found, uploading directly.")
        schema = {'utc': int, 'zone1': int, 'zone2': int,
                  'lat1': float, 'lon1': float, 'lat2': float, 'lon2': float,
                  'cnt': int, 'snr': int}
        bypass = lambda x: x
        total_rows   = count_csv_rows(out_file_name)
        total_chunks = max(1, (total_rows + batch_size - 1) // batch_size)
        print(f"[{reportSuffix}] Uploading {total_rows:,} rows → ClickHouse  ({total_chunks} chunk(s))")
        progress = Progress(f"[{reportSuffix}] →CH", total=total_rows)
        flush_list = []
        count = 0
        chunk = 0
        with open(out_file_name, 'r') as f:
            for row in ({k: schema.get(k, bypass)(v) for k, v in r.items()} for r in DictReader(f)):
                flush_list.append(row)
                count += 1
                if count == batch_size:
                    chunk += 1
                    clickhouseClient.execute(f'INSERT INTO default.{table_name} VALUES', flush_list)
                    progress.update(batch_size)
                    progress.tick(extra=f"  chunk {chunk}/{total_chunks}", force=True)
                    flush_list = []
                    count = 0
            if flush_list:
                clickhouseClient.execute(f'INSERT INTO default.{table_name} VALUES', flush_list)
                progress.update(len(flush_list))
        progress.finish()
    else:
        # No checkpoint — pipeline: decompress (thread) + CH upload (this thread) run simultaneously
        q: queue.Queue = queue.Queue(maxsize=2)   # backpressure: at most 2 batches in flight
        decomp = threading.Thread(
            target=_decompress_to_queue,
            args=(reportSuffix, q, batch_size, out_file_name),
            daemon=True,
        )
        decomp.start()
        _consume_queue(q)
        decomp.join()


@benchmark
def aggregate_15min_data(reportSuffix, clickhouseClient):
    minDT, maxDT = determineUTCminMax(reportSuffix, clickhouseClient)

    fetchDateStep1 = minDT.replace(hour=minDT.time().hour, minute=0, second=0, microsecond=0)
    fetchDateStep2 = fetchDateStep1 + timedelta(minutes=15)
    
    # make suitable array for min/max dates in selected range from DB
    counts = []
    while fetchDateStep2 <= maxDT:
        counts.append([fetchDateStep1.strftime('%Y-%m-%d'), fetchDateStep1.timestamp(), fetchDateStep2.timestamp()])
        fetchDateStep1 = fetchDateStep2
        fetchDateStep2 = fetchDateStep1 + timedelta(minutes=15)

    counts.append([fetchDateStep1.strftime('%Y-%m-%d'), fetchDateStep1.timestamp(), maxDT.timestamp()])
    # Get first day of month from reportSuffix

    processedZones = []
    list_bands = ['10m', '12m', '15m', '17m', '20m', '30m', '40m', '60m', '80m', '160m']

    # for item in counts:
    #     day = item[0]
    #     startUTC = item[1]
    #     endUTC = item[2]
    #
    #
    #     for zone1 in range(1, 76):
    #         for zone2 in range(1, 76):
    #             if (zone2 in processedZones):
    #                 continue
    #
    #             for band in list_bands:
    #
    #
    #         processedZones.insert(0, zone1)



def processReportFiles():
    # reportSuffix = ["2023-01-01", "2023-01-04", "2023-01-06", "2023-01-08", "2023-01-11"]
    # reportSuffix = ["2023-01-12"]
    # reportSuffix = ["2023-01-14", "2023-01-15", "2023-01-17", "2023-01-19"]
    # reportSuffix = ["2023-01-21", "2023-01-23"]
    # reportSuffix = ["2023-01-24", "2023-01-26"]
    # reportSuffix = ["2023-01-28", "2023-01-30", "2023-01-31"]

    # reportSuffix = ["2023-02-02", "2023-02-04", "2023-02-07", "2023-02-08", "2023-02-10"]
    # reportSuffix = ["2023-02-12", "2023-02-14", "2023-02-15", "2023-02-17", "2023-02-19", "2023-02-21", "2023-02-22", "2023-02-24", "2023-02-26", "2023-02-28" ]

    # reportSuffix = ["2023-03-01", "2023-03-03", "2023-03-05", "2023-03-07", "2023-03-08", "2023-03-10", "2023-03-12", "2023-03-14", "2023-03-15", "2023-03-17", "2023-03-19", "2023-03-21", "2023-03-22", "2023-03-24"]
    # reportSuffix = ["2023-03-26", "2023-03-28"]

    # reportSuffix = ["2024-07-02", "2024-07-03"]
    # reportSuffix = ["2024-07-05", "2024-07-07", "2024-07-09", "2024-07-10"]
    # reportSuffix = ["2024-07-12", "2024-07-16", "2024-07-17", "2024-07-19", "2024-07-21"]

    # reportSuffix = ["2024-07-23", "2024-07-24", "2024-07-26"]

    # reportSuffix = ["2024-07-28", "2024-07-30", "2024-07-31", "2024-08-02", "2024-08-04", "2024-08-06", "2024-08-07", "2024-08-09", "2024-08-11"]

    reportSuffix = ["2024-08-13"]

    # Each file is handled by one thread. Inside process_report_dump_file a second
    # daemon thread runs bz2 decompression while this thread uploads to ClickHouse,
    # so decompress + upload overlap for every file simultaneously.
    # Cap at 3 concurrent files: more parallel CH inserts do not help throughput
    # and increase memory pressure on the SummingMergeTree server.
    workers = min(3, len(reportSuffix))
    print(f"\n=== Processing {len(reportSuffix)} file(s) with {workers} thread(s) ===")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process_report_dump_file, r, connectToClickHouseDB()): r for r in reportSuffix}
        for f in as_completed(futures):
            report = futures[f]
            try:
                f.result()
                print(f"[{report}] done")
            except Exception as exc:
                print(f"[{report}] FAILED: {exc}")


def connectToClickHouseDB():
    try:
        client = Client.from_url('clickhouse://default:1q2w3e$R@172.27.188.228:9000/default')
        server_version = client.execute('SELECT version()')
        print("Connected to Clickhouse Server, version: {}".format(server_version[0][0]))
        return client
    except Exception as e:
        print("Error while connecting to Clickhouse", e)


def connectToMySQLDB(schemaName):
    try:
        connection = mysql.connector.connect(host='localhost', database=schemaName, user='root', password='1q2w3e$R')
        if connection.is_connected():
            db_Info = connection.get_server_info()
            print("Connected to MySQL Server, version: {}".format(db_Info))
            return connection
    except Exception as e:
        print("Error while connecting to MySQL", e)


@benchmark
def getStationZonesInfo():
    connection = connectToMySQLDB('main')
    cursor = connection.cursor(prepared=True)
    cursor.execute("select database();")
    cursor.fetchone()

    sql_zones_Query = "select id, ituZone, grid FROM main.ft8_stationinfo WHERE ituZone != 0;"

    cursor.execute(sql_zones_Query)
    dbData = cursor.fetchall()

    cursor.close()
    connection.close()

    dicZones = {t[0]: t[1:] for t in dbData}

    return dicZones


if __name__ == "__main__":
    try:
        startDT = datetime.now()
        print("CSV import program started at: " + str(startDT))
        dicZones = getStationZonesInfo()

        if len(dicZones) > 0:
            processReportFiles()
        else:
            print('Error - dicZones is empty')

        print(f"CSV import program ended at: {str(datetime.now())}, total time spent: {str(datetime.now() - startDT)}")
    except Exception as e:
        print("Processing error: ", e)
