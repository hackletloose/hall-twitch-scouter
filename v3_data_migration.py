import sqlite3
import csv
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv()
DB_HOST = os.getenv('DATABASE_HOST')
DB_PORT = os.getenv('DATABASE_PORT')
DB_NAME = os.getenv('DATABASE_NAME')
DB_USER = os.getenv('DATABASE_USER')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD')
v2_database_path = os.getenv('DATABASE_PATH')
v2_temp_csv_path = './data/v2_data_export.csv'

def export_sqlite_to_csv():
    try:
        connection = sqlite3.connect(v2_database_path)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM streamers")
        rows = cursor.fetchall()
        with open(v2_temp_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow([i[0] for i in cursor.description])
            csvwriter.writerows(rows)
        print(f"Data of SQLite-DB successfully exported to '{v2_temp_csv_path}'.")
    except sqlite3.Error as e:
        print(f"Error on Export from SQLite-DB: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def import_csv_to_mariadb():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS streamers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) UNIQUE,
                status VARCHAR(255),
                steam_id VARCHAR(255),
                player_ingame_name VARCHAR(255),
                further_infos TEXT,
                last_updated TIMESTAMP,
                show_later_until TIMESTAMP
            )
        ''')
        with open(v2_temp_csv_path, 'r', encoding='utf-8') as csvfile:
            csvreader = csv.reader(csvfile)
            next(csvreader)
            for row in csvreader:
                show_later_until = row[7] if row[7] else None
                cursor.execute('''
                    INSERT INTO streamers (id, name, status, steam_id, player_ingame_name, further_infos, last_updated, show_later_until)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    status = VALUES(status),
                    steam_id = VALUES(steam_id),
                    player_ingame_name = VALUES(player_ingame_name),
                    further_infos = VALUES(further_infos),
                    last_updated = VALUES(last_updated),
                    show_later_until = VALUES(show_later_until)
                ''', (row[0], row[1], row[2], row[3], row[4], row[5], row[6], show_later_until))
        connection.commit()
        print(f"Successfully imported Data to '{DB_NAME}'. You are ready for V3.")
    except Error as e:
        print(f"Error on Import to MariaDB: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

export_sqlite_to_csv()
import_csv_to_mariadb()
