import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')
STREAM_GAME_ID = os.getenv('STREAM_GAME_ID')
STREAM_LANGUAGE = os.getenv('STREAM_LANGUAGE')

def get_twitch_token():
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    try:
        response = requests.post(url, params=params, timeout=10)  # Timeout hinzugefügt
        response.raise_for_status()  # Hebt HTTP-Fehler hervor (4xx, 5xx)
        return response.json().get('access_token')
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred: {req_err}")
    except ValueError:
        print("Error decoding JSON response.")
    return None

def get_streamers(token):
    url = 'https://api.twitch.tv/helix/streams'
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    params = {
        'game_id': STREAM_GAME_ID,
        'language': STREAM_LANGUAGE
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred: {req_err}")
    except ValueError:
        print("Error decoding JSON response.")
    return []
