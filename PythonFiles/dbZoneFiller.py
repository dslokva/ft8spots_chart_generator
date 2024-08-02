import mysql.connector
from mysql.connector import Error
import ctypes
import os

dir = os.path.dirname(__file__)

# load dll
chart_gen = ctypes.WinDLL(f'{dir}/Ft8ChartGen.dll')
chart_gen.SquareToItuZone.argtypes = [ctypes.c_wchar_p]
commit_part_count = 1000

try:
    connection = mysql.connector.connect(host='10.169.11.200', database='main', user='user', password='1q2w3e$R')
    if connection.is_connected():
        db_Info = connection.get_server_info()
        print("Connected to MySQL Server version ", db_Info)
        cursor = connection.cursor()
        cursor.execute("select database();")
        record = cursor.fetchone()
        print("You're connected to database: ", record)

        sql_select_Query = "select id, callsign, grid from main.ft8_stationinfo where ituZone = 0 and grid != ''"
        cursor = connection.cursor(prepared=True)
        cursor.execute(sql_select_Query)
        # get all records
        records = cursor.fetchall()
        row_cnt = cursor.rowcount

        print("Total number of rows in table: ", row_cnt)
        countToCommit = 0
        if row_cnt > 0:
            updates = []

            for row in records:
                id = row[0]
                square = row[2]

                zone = chart_gen.SquareToItuZone(square)
                if (zone == 0):
                    zone = -1
                    print("Incorrect entry: id=", id, " callsign=", row[1], " square=", square)
                    #TODO: additional check, for first 4 chars of grid (if it already not 4 chars len).
                else:
                    tuple1 = (id, zone)
                    updates.append(tuple1)

            cursor.execute("""
            CREATE TEMPORARY TABLE temp_updates (
                id INT PRIMARY KEY,
                ituZone INT
            );
            """)

            insert_query = "INSERT INTO temp_updates (id, ituZone) VALUES (%s, %s)"
            cursor.executemany(insert_query, updates)

            update_query = """
            UPDATE main.ft8_stationinfo AS main
            JOIN temp_updates AS temp
            ON main.id = temp.id
            SET main.ituZone = temp.ituZone;
            """
            cursor.execute(update_query)
            connection.commit()

except Error as e:
    print("Error while connecting to MySQL", e)

finally:
    if connection:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")
