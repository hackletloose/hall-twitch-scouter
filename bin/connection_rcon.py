import requests
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("connection_rcon.log"),
        logging.StreamHandler()
    ]
)

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

async def search_player_on_apis(player_name, interaction):
    logging.info(f"Searching for player: {player_name} across APIs.")
    for i in range(1, 31):
        api_url = os.getenv(f'API_URL_{i}')
        api_key = os.getenv(f'API_KEY_{i}')
        if not api_url:
            logging.debug(f"API_URL_{i} not found, skipping.")
            continue
        logging.info(f"Using API {i}: {api_url}")
        if not api_key:
            found_in_api = await search_in_rcon(api_url, player_name, interaction)
        else:
            found_in_api = await search_in_rcon(api_url, player_name, interaction, api_key)
        if found_in_api:
            logging.info(f"Player {player_name} found in API {i}.")
            return
    logging.info(f"Player {player_name} not found in any API.")
    await interaction.followup.send("Player not found", ephemeral=True)

async def search_in_rcon(api_url, gesuchter_spieler, interaction, api_key=None):
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
        logging.debug(f"API Key provided for {api_url}.")
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        logging.info(f"Successful response from {api_url}.")
        
        try:
            data = response.json()
            if isinstance(data, dict) and "result" in data and "stats" in data["result"]:
                for spieler in data["result"]["stats"]:
                    if gesuchter_spieler in spieler['player'].lower():
                        message = f"Player: {spieler['player']}, Player ID: {spieler['player_id']}"
                        logging.info(f"Player {spieler['player']} found with Player ID {spieler['player_id']}.")
                        await interaction.followup.send(message, ephemeral=True)
                        return True
            logging.info(f"Player {gesuchter_spieler} not found in {api_url} response.")
            return False
        except ValueError:
            logging.error(f"Error processing JSON data from API: {api_url}")
            return False

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logging.error(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        logging.error(f"An error occurred: {req_err}")
    
    return False
