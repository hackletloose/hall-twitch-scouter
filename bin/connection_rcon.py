import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

async def search_player_on_apis(player_name, interaction):
    for i in range(1, 31):
        api_url = os.getenv(f'API_URL_{i}')
        api_key = os.getenv(f'API_KEY_{i}')
        if not api_url:
            continue
        if not api_key:
            found_in_api = await search_in_rcon(api_url, player_name, interaction)
        else:
            found_in_api = await search_in_rcon(api_url, player_name, interaction, api_key)
        if found_in_api:
            return
    await interaction.followup.send("Player not found", ephemeral=True)

async def search_in_rcon(api_url, gesuchter_spieler, interaction, api_key=None):
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        try:
            data = response.json()
            if isinstance(data, dict) and "result" in data and "stats" in data["result"]:
                for spieler in data["result"]["stats"]:
                    if gesuchter_spieler in spieler['player'].lower():
                        message = f"Player: {spieler['player']}, Player ID: {spieler['player_id']}"
                        await interaction.followup.send(message, ephemeral=True)
                        return True
            return False
        except ValueError:
            print(f"Fehler beim Verarbeiten der JSON-Daten von API: {api_url}")
            return False
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP-Fehler aufgetreten: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Verbindungsfehler aufgetreten: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout-Fehler aufgetreten: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Ein Fehler ist aufgetreten: {req_err}")
    return False
