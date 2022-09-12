import bz2
import os
import sys
from csv import DictReader
import mysql.connector
from threading import Thread
from datetime import datetime
from clickhouse_driver import Client

workDir = os.path.dirname(os.path.realpath(__file__))


def decompressAndAlterReportFile(reportSuffix, dicZones):
    report_bz2_path = f"H:/PskReporterDATA/report-{reportSuffix}.sql.bz2"

    spots_path = workDir + f"/spots-{reportSuffix}.csv"
    spots_path = spots_path.replace("\\", "/")
    spot_count = 0
    strPrefix = "INSERT INTO `report` VALUES ("
    #    out_file_header = "spotId,utc,band,zone1,zone2\n"
    out_file_header = "utc,band,zone1,zone2,dxcc1,dxcc2\n"
    bunchsize = 1024288  # Experiment with different sizes
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
                                    # spot = fields[0] + "," + fields[9] + "," + fields[14][1:-1] + "," + str(zone1[0]) + "," + str(zone2[0]) + "\n"
                                    spot = fields[9] + "," + fields[14][1:-1] + "," + str(zone1[0]) + "," + str(zone2[0]) + "," + str(
                                        fields[12]) + "," + str(fields[13]) + "\n"
                                    bunch.append(spot)
                                    spot_count += 1

                                    if len(bunch) == bunchsize:
                                        out_file.writelines(bunch)
                                        bunch = []
                                        print(f"Spot bulk write, count: {spot_count}")
                out_file.writelines(bunch)
                out_file.close()
                print("Time spent to alter report file: " + str(datetime.now() - startDT) + ", spots count: " + str(spot_count))
                return out_file.name
    else:
        return spots_path


def determineUTCminMax(reportSuffix):
    report_csv_path = f"{workDir}/spots-{reportSuffix}.csv"
    utcMax = 0
    utcMin = sys.maxsize
    with open(report_csv_path, mode='r') as in_file:
        for line in in_file:
            if (utcMax == 0):
                utcMax = 1
                continue

            utc = int(line.split(",")[0])
            if (utc > utcMax):
                utcMax = utc

            if (utc < utcMin):
                utcMin = utc

    return utcMin, utcMax


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


def process_report_dump_file(report, clickhouseClient):
    # First - process original bz2 sqldump file and create reduced csv file
    out_file_name = decompressAndAlterReportFile(report, dicZones)

    # Second - load this file into clickhouse
    if clickhouseClient:
        startDT = datetime.now()
        clickhouseClient.execute(
            'CREATE TABLE IF NOT EXISTS default.spots('
            '`utc` Int32, '
            '`band` String, '
            '`zone1` Int32, '
            '`zone2` Int32, '
            '`dxcc1` Int32, '
            '`dxcc2` Int32 '
            ') ENGINE = Log;')
        out_file_name = 'spots-' + report + '.csv'

        schema = {
            'utc': int,
            'zone1': int,
            'zone2': int,
            'dxcc1': int,
            'dxcc2': int,
        }
        bypass = lambda x: x

        batch_size = 1000000
        count = 0
        flush_list = []
        print(f"Report {out_file_name} - start upload to clickhouse timestamp: {str(startDT)}")
        with open(out_file_name, 'r') as f:
            csv_gen = ({k: schema.get(k, bypass)(v) for k, v in row.items()} for row in DictReader(f))
            i = 1
            for row in csv_gen:
                flush_list.append(row)
                count += 1
                if count == batch_size:
                    clickhouseClient.execute('INSERT INTO default.spots VALUES', flush_list)
                    print(f"Processed chunk #{i}, total count: {batch_size*i}")
                    flush_list = []
                    count = 0
                    i += 1
            clickhouseClient.execute('INSERT INTO default.spots VALUES', flush_list)
            print(f"Processed chunk #{i}, total count: {count}")

        print(f"Report {out_file_name} upload to clickhouse complete, time spent: {str(datetime.now() - startDT)}")
    else:
        print("No valid Clickhouse client")

    # startDT = datetime.now()
    # minDT, maxDT = determineUTCminMax(report)
    # print(f"determineUTCminMax {report} op complete, time spent: {str(datetime.now() - startDT)}")
    #
    # with open('./minMaxUTC.txt', 'a+') as minMaxUTCFile:
    #     minMaxUTCFile.write(f"{report}:{minDT}:{maxDT}\n")

    # fetchDateStep1 = minDT.replace(hour=minDT.time().hour, minute=0, second=0, microsecond=0, tzinfo=pytz.utc)
    # fetchDateStep2 = fetchDateStep1 + timedelta(minutes=15)
    #
    # # make suitable array for min/max dates in selected range from DB
    # counts = []
    # while fetchDateStep2 <= maxDT:
    #     counts.append([fetchDateStep1.timestamp(), zone1, zone2, band, 0, 0])
    #     fetchDateStep1 = fetchDateStep2
    #     fetchDateStep2 = fetchDateStep1 + timedelta(minutes=15)
    #
    # if (fetchDateStep1 <= maxDT):
    #     counts.append([fetchDateStep1.timestamp(), zone1, zone2])


def processReportFiles():
    reportSuffix = ["2022-02-06", "2022-02-09", "2022-02-11", "2022-02-13", "2022-02-16", "2022-02-18", "2022-02-20", "2022-02-23", "2022-02-25", "2022-02-27"]
    clickhouseConnect = connectToClickHouseDB()
    for report in reportSuffix:
        process_report_dump_file(report, clickhouseConnect)
        # thread = Thread(target=process_report_dump_file, args=(report, connectToClickHouseDB(),))
        # thread.start()


def connectToClickHouseDB():
    try:
        client = Client.from_url('clickhouse://localhost:9000/default')
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


def getStationZonesInfo():
    connection = connectToMySQLDB('main')
    cursor = connection.cursor(prepared=True)
    cursor.execute("select database();")
    cursor.fetchone()

    sql_zones_Query = "select id, ituZone FROM main.ft8_stationinfo WHERE ituZone != 0;"

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
        print("fetched stations/zones info, time spent total: " + str(datetime.now() - startDT))

        if len(dicZones) > 0:
            processReportFiles()
        else:
            print('Error - dicZones is empty')

        print(f"CSV import program ended at: {str(datetime.now())}, total time spent: {str(datetime.now() - startDT)}")
    except Exception as e:
        print("Processing error: ", e)
