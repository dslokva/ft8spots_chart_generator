import mysql.connector
from mysql.connector import Error
import ctypes
import os

dir = os.path.dirname(__file__)

# load dll
chart_gen = ctypes.WinDLL(f'{dir}/Ft8ChartGen.dll')
chart_gen.SquareToItuZone.argtypes = [ctypes.c_wchar_p]

try:
    connection = mysql.connector.connect(host='localhost', database='main', user='root', password='1q2w3e$R')
    if connection.is_connected():
        db_Info = connection.get_server_info()
        print("Connected to MySQL Server version ", db_Info)
        cursor = connection.cursor()
        cursor.execute("select database();")
        record = cursor.fetchone()
        print("You're connected to database: ", record)

        sql_select_Query = "select id, callsign, grid from main.ft8_stationinfo where ituZone = 0"
        cursor = connection.cursor(prepared=True)
        cursor.execute(sql_select_Query)
        # get all records
        records = cursor.fetchall()
        print("Total number of rows in table: ", cursor.rowcount)
        countToCommit = 0
        for row in records:
            id = row[0]
            square = row[2]

            zone = chart_gen.SquareToItuZone(square)
            if (zone == 0):
                zone = -1
                print("Incorrect entry: id=", id, " callsign=", row[1], " square=", square)
            else:
                mySql_update_query = """UPDATE main.ft8_stationinfo SET ituZone = %s where id = %s"""
                tuple1 = (zone, id)
                cursor.execute(mySql_update_query, tuple1)
                countToCommit += 1

        print(f"Commit transaction. Total rows = {countToCommit}")
        connection.commit()

except Error as e:
    print("Error while connecting to MySQL", e)

finally:
    if connection:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")