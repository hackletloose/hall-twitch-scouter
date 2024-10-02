import requests
import os
from dotenv import load_dotenv
import time

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
    for attempt in range(retries):
        try:
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get('access_token')
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(5)
        except ValueError:
            print("Error decoding JSON response.")
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
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{retries} to fetch streamers failed: {e}")
            if attempt < retries - 1:
                time.sleep(5)
        except ValueError:
            print("Error decoding JSON response.")
    return []
