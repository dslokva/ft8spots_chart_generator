import calendar
import logging
import time
from datetime import datetime, timedelta
import mysql.connector
import pytz as pytz
from mysql.connector import Error



def connectToDB(schema):
    global connection
    global schemaName

    schemaName = schema
    try:
        connection = mysql.connector.connect(host='localhost', database=schemaName, user='root', password='HpsFq25sxx@')
        #connection = mysql.connector.connect(host='34.141.6.80', database=schemaName, user='root', password='F5qjhqD2FE10DPsG')
        if connection.is_connected():
            db_Info = connection.get_server_info()
            logger.info("Connected to MySQL Server version %s", db_Info)

            cursor = connection.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()

            logger.info("You're connected to database: %s", record)
            return connection.cursor(prepared=True)
    except Error as e:
        logger.error("Error while connecting to MySQL", e)


def initLogger():
    global logger

    logger = logging.getLogger('dbReportCounter')
    logger.setLevel(logging.DEBUG)


def setLoggerFileNamePrefix(filePrefixName):
    fileDTLabel = time.strftime("%Y%m%d-%H%M%S")
    logger = logging.getLogger('dbReportCounter')

    for hdlr in logger.handlers[:]:  # remove all old handlers
        logger.removeHandler(hdlr)

    fh = logging.FileHandler(filePrefixName+'_'+fileDTLabel+'.log')
    fh.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s | %(levelname)s | %(message)s')
    fh.setFormatter(formatter)

    logger.addHandler(fh)


def getSpotCountsFromReportTable(cursor, year, zone1, zone2, band, reportTableName, countTableName):
    spotcount = 0

    try:
        sql_band_Query = "SELECT avg(Tr.sNR), count(Tr.mode), Tr.flowStartSeconds FROM " + schemaName + "." + reportTableName + " as Tr " \
                         " JOIN ( SELECT at.ituZone as ZoneS, at.id FROM " + schemaName + ".ft8_stationinfo at) b ON (Tr.senderInfoId = b.id)" \
                         " JOIN ( SELECT at.ituZone as ZoneR, at.id FROM " + schemaName + ".ft8_stationinfo at) c ON (Tr.receiverInfoId = c.id)" \
                         " where ZoneS = %s and ZoneR = %s and Tr.band = %s group by Tr.flowStartSeconds order by Tr.flowStartSeconds"

        # first we get all spot counts for selected zones and band
        sqlParams = (zone1, zone2, band)
        cursor.execute(sql_band_Query, sqlParams)
        partCounts = cursor.fetchall()

        if (cursor.rowcount == 0):
            return 0 

        # select maximum and minimum time for selected spotsFile
        minDT = datetime.fromtimestamp(partCounts[0][2], tz=pytz.utc)
        maxDT = datetime.fromtimestamp(partCounts[len(partCounts)-1][2], tz=pytz.utc)

        fetchDateStep1 = minDT.replace(hour=minDT.time().hour, minute=0, second=0, microsecond=0, tzinfo=pytz.utc)
        fetchDateStep2 = fetchDateStep1 + timedelta(minutes=15)

        # make suitable array for min/max dates to fill next
        counts = []
        while fetchDateStep2 <= maxDT:
            counts.append([fetchDateStep1.timestamp(), zone1, zone2, band, 0, 0])
            fetchDateStep1 = fetchDateStep2
            fetchDateStep2 = fetchDateStep1 + timedelta(minutes=15)

        if (fetchDateStep1 <= maxDT):
            counts.append([fetchDateStep1.timestamp(), zone1, zone2, band, 0, 0])


        for part in partCounts:
            sumAvgSNR = part[0]
            sumCnt = part[1]
            utc = part[2]

            for (index, a_tuple) in enumerate(counts):
                if (utc >= a_tuple[0] and utc < a_tuple[0] + 900):
                    list_to_change = counts.pop(index)
                    list_to_change[4] = sumCnt
                    list_to_change[5] = float(sumAvgSNR)
                    counts.insert(index, list_to_change)
                    continue

        #clear zero values
        counts = [x for x in counts if x[4] != 0]

        for spotInfo in counts:
            sql_insert_Query = "INSERT INTO "+schemaName+"."+countTableName+" (`idzone_1`, `idzone_2`, `band`, `utc`, `spot_count`, `spot_snr`)" \
                               " VALUES (%s, %s, %s, %s, %s, %s);"
            sqlParams = (spotInfo[1], spotInfo[2], spotInfo[3], spotInfo[0], spotInfo[4], spotInfo[5])

            cursor.execute(sql_insert_Query, sqlParams)
            connection.commit()
            spotcount += spotInfo[4]

            if (cursor.rowcount > 0):
                logger.info("Inserted UTC: %s, avgSNR: %s, spotsCnt: %s", str(spotInfo[0]), str(spotInfo[5]), str(spotInfo[4]))


    except Error as e:
        logger.error("Error while connecting to MySQL: %s", e)

    finally:
        return spotcount


def processCountsForBand(band):
    processedZones = []
    timebandstart = datetime.now()
    setLoggerFileNamePrefix(band+'_report_2021_09_05')

    for zone1 in range(1, 76):
        for zone2 in range(1, 76):
            if (zone2 in processedZones):
                continue

            logger.info("Section start. %s, [%s-%s]", band, str(zone1), str(zone2))
            spotCount = getSpotCountsFromReportTable(cursor, 2021, zone1, zone2, band, 'report_2021_09_05', 'zone_counts_2021_09_05')
            if (spotCount > 0):
                logger.info("Section end. %s, [%s-%s], spot count sum: %s", band, str(zone1), str(zone2), str(spotCount))
                print("Section end. " + band + " [" + str(zone1) + " - " + str(zone2) + "], spot count sum: " + str(spotCount))
            else:
                logger.info("----------------------")

        processedZones.insert(0, zone1)

    logger.info("Time spent for %s band: %s", band, str(datetime.now() - timebandstart))
    print("Time spent for " + band + " band: " + str(datetime.now() - timebandstart))


if __name__ == "__main__":
    bands = [ '60m', '160m']

    initLogger()

    try:
        cursor = connectToDB('main')
        timestart = datetime.now()

        for band in bands:
            processCountsForBand(band)

        logger.info("Time spent total for all bands in all zones combination is: %s", str(datetime.now()-timestart))
        print("Time spent total for all bands in all zones combination is: " + str(datetime.now()-timestart))

    except Error as e:
        logger.error('Error while connecting to MySQL: %s', e)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logger.info("MySQL connection is closed")



#dir = os.path.dirname(__file__)

# load dll
# chart_gen = ctypes.WinDLL(f'{dir}/Ft8ChartGen_v1.dll')
# chart_gen.SquareToItuZone.argtypes = [ctypes.c_wchar_p]
# chart_gen.GenerateChart.argtypes = [ctypes.c_wchar_p]

# test GenerateChart
# some reference calculations for one band
# 96 digits per day
# 35040 or 34944 per year
# 2880 or 2976 per month

#counts = [int(s) for s in open(f'{dir}/counts.txt', 'r').readlines()]
#params = {"year": 2021, "itu_zone_1": 30, "itu_zone_2": 18, "band_meters": 40, "output_folder": dir, "ap": [10] * 366, "counts": counts}
#params = json.dumps(params)
#rc = chart_gen.GenerateChart(params)
#print(f"GenerateChart() returned code: {rc}")