import bz2
import os
import sys
from csv import DictReader
import mysql.connector
from threading import Thread
from datetime import datetime, timedelta
from clickhouse_driver import Client
import pytz
import time
from functools import wraps
import maidenhead as mh


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



@benchmark
def decompressAndAlterReportFile(reportSuffix, dicZones):
    report_bz2_path = f"d:/Source/ft8spots_chart_generator/ExampleFiles/report-{reportSuffix}.sql.bz2"
    # report_bz2_path = f"g:/PskReporterDATA/report-{reportSuffix}.sql.bz2"
    print(f"Start decompressing file: {report_bz2_path}")

    spots_path = workDir + f"/../ExampleFiles/spots-sum-grid-ll-{reportSuffix}.csv"
    spots_path = spots_path.replace("\\", "/")
    spot_count = 0
    strPrefix = "INSERT INTO `report` VALUES ("
    #    out_file_header = "spotId,utc,band,zone1,zone2\n"
    # out_file_header = "utc,band,zone1,zone2,dxcc1,dxcc2\n"
    # out_file_header = "utc,band,zone1,zone2,cnt\n"
    out_file_header = "utc,band,zone1,zone2,grid1,grid2,lat1,lon1,lat2,lon2,cnt\n"
    bunchsize = 512000  # Experiment with different sizes
    bunch = []

    # if altered report file not exists - will make it
    if not os.path.exists(spots_path):
        with bz2.BZ2File(report_bz2_path, "r") as in_file:
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

                                    # spot = fields[9] + "," + fields[14][1:-1] + "," + str(zone1[0]) + "," + str(zone2[0]) + "," + str(fields[12]) + "," + str(fields[13]) + "\n"
                                    spot = fields[9] + "," + fields[14][1:-1] + "," + str(zone1[0]) + "," + str(zone2[0]) + "," + grid1 + "," + grid2 + "," + str(lat1) + "," + str(lon1) + "," + str(lat2) + "," + str(lon2) +",1\n"
                                    bunch.append(spot)
                                    spot_count += 1

                                    if len(bunch) == bunchsize:
                                        out_file.writelines(bunch)
                                        bunch = []
                                        print(f"Spot bulk write into csv file, row count: {spot_count}")
                out_file.writelines(bunch)
                out_file.close()
                return out_file.name
    else:
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


@benchmark
def process_report_dump_file(reportSuffix, clickhouseClient):
    if clickhouseClient:
        out_file_name = 'd:/Source/ft8spots_chart_generator/ExampleFiles/spots-sum-grid-ll-' + reportSuffix + '.csv'
        tableSuffix = reportSuffix[:7].replace("-","_")

        # simple exists check
        if os.path.isfile(out_file_name):
            print(f"Report {out_file_name} already exists. Skipping processing from bz2 to csv.")
        else:
            # Process original bz2 sqldump file and create reduced csv file
            decompressAndAlterReportFile(reportSuffix, dicZones)

        clickhouseClient.execute(
            f'CREATE TABLE IF NOT EXISTS default.spots_sum_grid_ll_{tableSuffix}'
            '(`utc` Int32, '
            '`band` String, '
            '`zone1` Int32, '
            '`zone2` Int32, '
            '`grid1` String, '
            '`grid2` String, '
            '`lat1` Float64, '
            '`lon1` Float64, '
            '`lat2` Float64, '
            '`lon2` Float64, '            
            '`cnt` UInt8 '
            # '`dxcc1` Int32, '
            # '`dxcc2` Int32 '
            ')ENGINE = SummingMergeTree '
            'ORDER BY (utc, band, zone1, zone2, grid1, grid2, lat1, lon1, lat2, lon2) '
            'PARTITION BY toYYYYMMDD(toDateTime(utc)) '
            'PRIMARY KEY (utc, band, zone1, zone2, grid1, grid2, lat1, lon1, lat2, lon2); ')

        schema = {
            'utc': int,
            'zone1': int,
            'zone2': int,
            'lat1': float,
            'lon1': float,
            'lat2': float,
            'lon2': float,
            'cnt': int,
            # 'dxcc1': int,
            # 'dxcc2': int,
        }
        bypass = lambda x: x

        batch_size = 2048000
        count = 0
        flush_list = []

        print(f"Open csv file for upload to ch: {out_file_name}")
        with open(out_file_name, 'r') as f:
            csv_gen = ({k: schema.get(k, bypass)(v) for k, v in row.items()} for row in DictReader(f))
            i = 1
            for row in csv_gen:
                flush_list.append(row)
                count += 1
                if count == batch_size:
                    clickhouseClient.execute(f'INSERT INTO default.spots_sum_grid_ll_{tableSuffix} VALUES', flush_list)
                    print(f"Processed chunk #{i}, total count: {batch_size*i}")
                    flush_list = []
                    count = 0
                    i += 1
            clickhouseClient.execute(f'INSERT INTO default.spots_sum_grid_ll_{tableSuffix} VALUES', flush_list)
            print(f"Processed chunk #{i}, total count: {count}")

        print(f"Report {out_file_name} upload to clickhouse complete.")
    else:
        print("No valid Clickhouse client")


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
    #reportSuffix = ["2023-01-14", "2023-01-15", "2023-01-17", "2023-01-19"]
    # reportSuffix = ["2023-01-21", "2023-01-23"]
    # reportSuffix = ["2023-01-24", "2023-01-26"]
    # reportSuffix = ["2023-01-28", "2023-01-30", "2023-01-31"]

    # reportSuffix = ["2023-02-02", "2023-02-04", "2023-02-07", "2023-02-08", "2023-02-10"]
    # reportSuffix = ["2023-02-12", "2023-02-14", "2023-02-15", "2023-02-17", "2023-02-19", "2023-02-21", "2023-02-22", "2023-02-24", "2023-02-26", "2023-02-28" ]

    # reportSuffix = ["2023-03-01", "2023-03-03", "2023-03-05", "2023-03-07", "2023-03-08", "2023-03-10", "2023-03-12", "2023-03-14", "2023-03-15", "2023-03-17", "2023-03-19", "2023-03-21", "2023-03-22", "2023-03-24"]
    # reportSuffix = ["2023-03-26", "2023-03-28"]
    reportSuffix = ["2024-07-14"]

    clickhouseConnect = connectToClickHouseDB()
    for report in reportSuffix:
        if process_report_dump_file(report, clickhouseConnect):
           pass
        # TODO: change to month calc
        # aggregate_15min_data(month, clickhouseConnect)
        # thread = Thread(target=process_report_dump_file, args=(report, connectToClickHouseDB(),))
        # thread.start()


def connectToClickHouseDB():
    try:
        client = Client.from_url('clickhouse:/172.24.68.104:9000/default')
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
