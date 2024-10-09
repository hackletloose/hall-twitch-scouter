import mysql.connector
from dotenv import load_dotenv
from mysql.connector import pooling, Error
from datetime import datetime, timedelta
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DB_HOST = os.getenv('DATABASE_HOST')
DB_PORT = os.getenv('DATABASE_PORT')
DB_NAME = os.getenv('DATABASE_NAME')
DB_USER = os.getenv('DATABASE_USER')
DB_TABLE = os.getenv('DATABASE_TABLE')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD')

connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    pool_reset_session=True,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

def get_db_connection():
    return connection_pool.get_connection()

def create_or_update_table():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS `{DB_TABLE}` (
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
                connection.commit()
    except Error as e:
        print(f"Error: {e}")

def store_streamer_in_db(streamer_name, status=None, steam_id=None, player_ingame_name=None, further_infos=None):
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'''
                    SELECT status, steam_id, player_ingame_name, further_infos 
                    FROM `{DB_TABLE}` WHERE name = %s
                ''', (streamer_name,))
                result = cursor.fetchone()
                if result:
                    existing_status, existing_steam_id, existing_player_ingame_name, existing_further_infos = result
                    status = status or existing_status
                    steam_id = steam_id or existing_steam_id
                    player_ingame_name = player_ingame_name or existing_player_ingame_name
                    further_infos = further_infos or existing_further_infos
                cursor.execute(f'''
                    INSERT INTO `{DB_TABLE}` (name, status, steam_id, player_ingame_name, further_infos, last_updated, show_later_until)
                    VALUES (%s, %s, %s, %s, %s, %s, NULL)
                    ON DUPLICATE KEY UPDATE
                        status = VALUES(status),
                        steam_id = VALUES(steam_id),
                        player_ingame_name = VALUES(player_ingame_name),
                        further_infos = VALUES(further_infos),
                        last_updated = VALUES(last_updated),
                        show_later_until = NULL
                ''', (streamer_name, status, steam_id, player_ingame_name, further_infos, datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
                connection.commit()
    except Error as e:
        print(f"Error: {e}")

def update_show_later(streamer_name, show_later_until):
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'''
                    UPDATE `{DB_TABLE}`
                    SET show_later_until = %s
                    WHERE name = %s
                ''', (show_later_until, streamer_name))
                connection.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

def fetch_info_from_db(streamer_name):
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT steam_id, player_ingame_name, further_infos FROM `{DB_TABLE}` WHERE name = %s', (streamer_name,))
                result = cursor.fetchone()
                if result:
                    return result[0], result[1], result[2]
                return None, None, None
    except Error as e:
        print(f"Error: {e}")
        return None, None, None

def should_display_streamer(streamer_name, CERTIFY_DAYS, UNWANTED_DAYS, IRRELEVANT_DAYS):
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT status, last_updated, show_later_until FROM `{DB_TABLE}` WHERE name = %s', (streamer_name,))
                result = cursor.fetchone()
                status, last_updated = None, None
                if result:
                    status, last_updated, show_later_until = result
                    now = datetime.now()
                    if show_later_until and now < show_later_until:
                        return False, status, last_updated
                    if status == 'certify' and now - last_updated < timedelta(days=CERTIFY_DAYS):
                        return False, status, last_updated
                    elif status in ['unwanted', 'irrelevant', 'console'] and now - last_updated < timedelta(days=UNWANTED_DAYS):
                        return False, status, last_updated
                return True, status, last_updated
    except Error as e:
        print(f"Error: {e}")
        return True, None, None

def delete_expired_streamers():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'''
                    DELETE FROM `{DB_TABLE}`
                    WHERE show_later_until IS NOT NULL AND show_later_until < NOW()
                ''')
                connection.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

def delete_old_streamers():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'''
                    DELETE FROM `{DB_TABLE}`
                    WHERE show_later_until IS NULL AND status = ''
                ''')
                connection.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
