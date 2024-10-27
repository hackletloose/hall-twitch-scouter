import requests
import os
import time
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("connection_twitch.log"),
        logging.StreamHandler()
    ]
)

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')
STREAM_GAME_ID = os.getenv('STREAM_GAME_ID')
STREAM_LANGUAGE = os.getenv('STREAM_LANGUAGE')

def get_twitch_token(retries=3):
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    logging.info("Attempting to retrieve Twitch access token.")
    for attempt in range(retries):
        try:
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            token = response.json().get('access_token')
            logging.info("Twitch access token retrieved successfully.")
            return token
        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                logging.info("Retrying in 5 seconds...")
                time.sleep(5)
        except ValueError:
            logging.error("Error decoding JSON response.")
    logging.error("Failed to retrieve Twitch access token after retries.")
    return None

def get_streamers(token, retries=3):
    url = 'https://api.twitch.tv/helix/streams'
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    params = {
        'game_id': STREAM_GAME_ID,
        'language': STREAM_LANGUAGE
    }
    logging.info("Attempting to retrieve streamers.")
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            streamers = response.json().get('data', [])
            logging.info(f"Successfully retrieved {len(streamers)} streamers.")
            return streamers
        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {attempt + 1}/{retries} to fetch streamers failed: {e}")
            if attempt < retries - 1:
                logging.info("Retrying in 5 seconds...")
                time.sleep(5)
        except ValueError:
            logging.error("Error decoding JSON response.")
    logging.error("Failed to retrieve streamers after retries.")
    return []
