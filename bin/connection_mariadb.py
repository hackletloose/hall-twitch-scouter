import mysql.connector
from mysql.connector import pooling, Error
from datetime import datetime, timedelta
import asyncio
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("connection_mariadb.log"),
        logging.StreamHandler()
    ]
)

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
                logging.info(f"Table `{DB_TABLE}` created or updated successfully.")
    except Error as e:
        logging.error(f"Error creating or updating table: {e}")

def store_streamer_in_db(streamer_name, status=None, steam_id=None, player_ingame_name=None, further_infos=None, update_last_updated=False):
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

                if update_last_updated:
                    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                else:
                    last_updated = None

                cursor.execute(f'''
                    INSERT INTO `{DB_TABLE}` 
                    (name, status, steam_id, player_ingame_name, further_infos, last_updated, show_later_until)
                    VALUES (%s, %s, %s, %s, %s, %s, NULL)
                    ON DUPLICATE KEY UPDATE
                        status = VALUES(status),
                        steam_id = VALUES(steam_id),
                        player_ingame_name = VALUES(player_ingame_name),
                        further_infos = VALUES(further_infos),
                        last_updated = IF(VALUES(last_updated) IS NOT NULL, VALUES(last_updated), last_updated),
                        show_later_until = NULL
                ''', (streamer_name, status, steam_id, player_ingame_name, further_infos, last_updated))
                connection.commit()
                logging.info(f"Streamer `{streamer_name}` has been stored/updated in the database.")
    except Error as e:
        logging.error(f"Error storing streamer in database: {e}")

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
                logging.info(f"Show later timestamp updated for `{streamer_name}` until {show_later_until}.")
    except Error as err:
        logging.error(f"Error updating show_later_until for `{streamer_name}`: {err}")

def fetch_info_from_db(streamer_name):
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'''
                    SELECT status, steam_id, player_ingame_name, further_infos 
                    FROM `{DB_TABLE}` 
                    WHERE name = %s
                ''', (streamer_name,))
                result = cursor.fetchone()
                logging.info(f"Database result for `{streamer_name}`: {result}")
                if result:
                    status, steam_id, player_ingame_name, further_infos = result
                    return status, steam_id, player_ingame_name, further_infos
                logging.info(f"No information found for `{streamer_name}`.")
                return None, None, None, None
    except Error as e:
        logging.error(f"Error fetching info from database for `{streamer_name}`: {e}")
        return None, None, None, None

def should_display_streamer(streamer_name, CERTIFY_DAYS, UNWANTED_DAYS, IRRELEVANT_DAYS):
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'''
                    SELECT status, last_updated, show_later_until 
                    FROM `{DB_TABLE}` 
                    WHERE name = %s
                ''', (streamer_name,))
                result = cursor.fetchone()
                status, last_updated, show_later_until = None, None, None
                if result:
                    status, last_updated, show_later_until = result
                    now = datetime.now()
                    if show_later_until and now < show_later_until:
                        return False, status, last_updated
                    if status == 'certify' and last_updated and (now - last_updated < timedelta(days=CERTIFY_DAYS)):
                        return False, status, last_updated
                    elif status in ['unwanted', 'irrelevant', 'console', '1st warn', '2nd warn'] and last_updated:
                        # Hier kann man UNWANTED_DAYS auch für '1st warn' / '2nd warn' anwenden, falls erwünscht
                        if (now - last_updated < timedelta(days=UNWANTED_DAYS)):
                            return False, status, last_updated
                return True, status, last_updated

    except Error as e:
        logging.error(f"Error checking if streamer `{streamer_name}` should be displayed: {e}")
        return True, None, None

def delete_expired_streamers():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'''
                    DELETE FROM `{DB_TABLE}`
                    WHERE show_later_until IS NOT NULL 
                    AND show_later_until < NOW()
                ''')
                connection.commit()
                logging.info(f"Expired streamers have been deleted from `{DB_TABLE}`.")
    except Error as err:
        logging.error(f"Error deleting expired streamers: {err}")

def delete_old_streamers():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'''
                    DELETE FROM `{DB_TABLE}`
                    WHERE show_later_until IS NULL 
                    AND (status = '' OR status IS NULL)
                ''')
                connection.commit()
                logging.info(f"Old streamers without status have been deleted from `{DB_TABLE}`.")
    except Error as err:
        logging.error(f"Error deleting old streamers: {err}")

async def fetch_status_from_db(streamer_name):
    try:
        status, _, _, _ = await asyncio.to_thread(fetch_info_from_db, streamer_name)
        logging.info(f"Fetched status for `{streamer_name}`: {status}")
        return status
    except Exception as e:
        logging.error(f"Error fetching status for streamer `{streamer_name}`: {e}")
        return None
