import requests
import os
import logging
from dotenv import load_dotenv

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
        server_name = os.getenv(f'API_NAME_{i}', f'API {i}')
        if not api_url:
            logging.debug(f"API_URL_{i} not found, skipping.")
            continue
        logging.info(f"Using API {i}: {api_url} (Server: {server_name})")
        if not api_key:
            found_in_api = await search_in_rcon(api_url, player_name, interaction, server_name=server_name)
        else:
            found_in_api = await search_in_rcon(api_url, player_name, interaction, api_key, server_name=server_name)
        if found_in_api:
            logging.info(f"Player {player_name} found in API {i}.")
            return
    logging.info(f"Player {player_name} not found in any API.")
    await interaction.followup.send("Player not found", ephemeral=True)


async def search_in_rcon(api_url, gesuchter_spieler, interaction, api_key=None, server_name="Unknown"):
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
                matching_players = []
                for spieler in data["result"]["stats"]:
                    if gesuchter_spieler in spieler['player'].lower():
                        # Hier wird der Servername hinzugefügt:
                        message = f"Server: {server_name} - Player: {spieler['player']}, Player ID: {spieler['player_id']}"
                        matching_players.append(message)
                
                if matching_players:
                    # Zeige maximal 10 Ergebnisse an
                    matching_players = matching_players[:10]
                    final_message = "\n".join(matching_players)
                    await interaction.followup.send(final_message, ephemeral=True)
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
