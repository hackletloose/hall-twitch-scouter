import discord
from discord.ext import tasks, commands
import requests
import sqlite3
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')
STREAM_GAME_ID = os.getenv('STREAM_GAME_ID')
STREAM_GAME_NAME = os.getenv('STREAM_GAME_NAME')
STREAM_LANGUAGE = os.getenv('STREAM_LANGUAGE')
DISCORD_CHANNEL_ID = int(os.getenv('REPORTS_DISCORD_CHANNEL_ID'))
UNWANTED_CHANNEL_ID = int(os.getenv('UNWANTED_DISCORD_CHANNEL_ID'))
CERTIFY_DAYS = int(os.getenv('CERTIFY_DAYS'))
UNWANTED_DAYS = int(os.getenv('UNWANTED_DAYS'))
IRRELEVANT_DAYS = int(os.getenv('IRRELEVANT_DAYS'))
CONSOLE_DAYS = int(os.getenv('CONSOLE_DAYS'))
HIDE_HOURS = int(os.getenv('HIDE_HOURS'))
DELETE_AFTER_ONLINE_TIME = int(os.getenv('DELETE_AFTER_ONLINE_TIME'))
reported_streamers = {}
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

DATABASE_PATH = 'streamers.db'

api_urls = [
    os.getenv('API_URL_1'),
    os.getenv('API_URL_2'),
    os.getenv('API_URL_3'),
    os.getenv('API_URL_4'),
    os.getenv('API_URL_5'),
    os.getenv('API_URL_6'),
    os.getenv('API_URL_7'),
    os.getenv('API_URL_8'),
    os.getenv('API_URL_9'),
    os.getenv('API_URL_10'),
    os.getenv('API_URL_11'),
    os.getenv('API_URL_12')
]

os.getenv('API_KEY_8')

class MyView(discord.ui.View):
    def __init__(self, streamer_name):
        super().__init__(timeout=None)
        self.streamer_name = streamer_name
        self.watching = False
    @discord.ui.button(label='👀 Start/Stop audit', style=discord.ButtonStyle.primary, custom_id='watch_button_id')
    async def watch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.watching:
            self.watching = True
            await interaction.response.send_message(f'**{interaction.user.name}** schaut dem Stream von **{self.streamer_name}** zu.')
        else:
            self.watching = False
            await interaction.response.send_message(f'**{interaction.user.name}** hat den Stream von **{self.streamer_name}** verlassen.')

    @discord.ui.button(label='👎 unwanted', style=discord.ButtonStyle.danger, custom_id='unwanted_button_id')
    async def unwanted(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(await MyModal.create('unwanted', self.streamer_name))

    @discord.ui.button(label='👍 certify', style=discord.ButtonStyle.success, custom_id='certify_button_id')
    async def certify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(await MyModal.create('certify', self.streamer_name))

#    @discord.ui.button(label='🎮 console player', style=discord.ButtonStyle.primary, custom_id='console_button_id')
#    async def console(self, interaction: discord.Interaction, button: discord.ui.Button):
#        store_streamer_in_db(self.streamer_name, status='console')
#        await interaction.response.send_message(f'**{interaction.user.name}**: Streamer **{self.streamer_name}** has been marked as **console player**.')

    @discord.ui.button(label='👋🎮 irrelevant', style=discord.ButtonStyle.primary, custom_id='irrelevant_button_id')
    async def irrelevant(self, interaction: discord.Interaction, button: discord.ui.Button):
        store_streamer_in_db(self.streamer_name, status='irrelevant')
        await interaction.response.send_message(f'{interaction.user.name}**: Streamer **{self.streamer_name}** has been marked as **irrelevant**.')

    @discord.ui.button(label='⏰ display later', style=discord.ButtonStyle.secondary, custom_id='show_later_button_id')
    async def show_later(self, interaction: discord.Interaction, button: discord.ui.Button):
        show_later_until = datetime.now() + timedelta(hours=HIDE_HOURS)
        update_show_later(self.streamer_name, show_later_until)
        await interaction.response.send_message(f'{interaction.user.name}**: Streamer **{self.streamer_name}** will not be shown up again for **{HIDE_HOURS} hours**')
        
    @discord.ui.button(label='🔍 search', style=discord.ButtonStyle.secondary, custom_id='search_player_button_id')
    async def search_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PlayerSearchModal())


class PlayerSearchModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title='Search Player')
        self.player_name_input = discord.ui.TextInput(
            label='player name',
            placeholder='Please input player name / player name part',
            custom_id='player_name_input'
        )
        self.add_item(self.player_name_input)

    async def on_submit(self, interaction: discord.Interaction):
        player_name = self.player_name_input.value.lower()
        await interaction.response.send_message(f'Searching for "{player_name}"...', ephemeral=True)  # Erste Antwort
        await search_player_on_apis(player_name, interaction)  # Keine zweite Antwort hier


class MyModal(discord.ui.Modal):
    def __init__(self, action, streamer_name, steam_id=None, player_ingame_name=None, further_infos=None):
        super().__init__(title='Assign Player Infos')
        self.action = action
        self.streamer_name = streamer_name
        self.steam_id_input = discord.ui.TextInput(
            label='Player-ID',
            placeholder='please input XBOX- or Steam-ID',
            custom_id=f'steam_id_input_{action}_{streamer_name}',
            default=steam_id or ''
        )
        self.player_ingame_name_input = discord.ui.TextInput(
            label='Player Ingame Name',
            placeholder='please input player ingame name',
            custom_id=f'player_ingame_name_input_{action}_{streamer_name}',
            default=player_ingame_name or '',
            max_length=255
        )
        self.further_infos_input = discord.ui.TextInput(
            label='Further Infos',
            placeholder='please input any additional information',
            custom_id=f'further_infos_input_{action}_{streamer_name}',
            default=further_infos or '',
            max_length=255
        )
        self.add_item(self.steam_id_input)
        if action == 'unwanted':
            self.add_item(self.player_ingame_name_input)
            self.add_item(self.further_infos_input)

    @classmethod
    async def create(cls, action, streamer_name):
        steam_id, player_ingame_name, further_infos = await fetch_info_from_db(streamer_name)
        return cls(action, streamer_name, steam_id=steam_id, player_ingame_name=player_ingame_name, further_infos=further_infos)

    async def on_submit(self, interaction: discord.Interaction):
        steam_id = self.steam_id_input.value
        player_ingame_name = self.player_ingame_name_input.value if self.action == 'unwanted' else None
        further_infos = self.further_infos_input.value if self.action == 'unwanted' else None
        store_streamer_in_db(self.streamer_name, status=self.action, steam_id=steam_id, player_ingame_name=player_ingame_name, further_infos=further_infos)
        if self.action == 'unwanted':
            await send_unwanted_report(interaction.user, self.streamer_name, steam_id, player_ingame_name, further_infos)
            await interaction.response.send_message(f'**{interaction.user.name}** descision: **{self.streamer_name}** with Player-ID **{steam_id}**, Ingame Name **{player_ingame_name}**, and Infos **{further_infos}** has been marked as **{self.action}**.')
        else:
            await interaction.response.send_message(f'**{interaction.user.name}** descision: **{self.streamer_name}** has been marked as **{self.action}**.')

async def send_unwanted_report(user, streamer_name, steam_id, player_ingame_name, further_infos):
    unwanted_channel = bot.get_channel(UNWANTED_CHANNEL_ID)
    message = (
        f'**Name:** {player_ingame_name}\n'
        f'**SteamID:** {steam_id}\n'
        f'**Steam-Profile:** https://steamcommunity.com/profiles/{steam_id}\n'
        f'**Type of issue:** Streaming without a map overlay or delay\n'
        f'**Description:** Streaming without a map overlay or delay, Weiteres: {further_infos}, **Twitch-URL:** https://twitch.tv/{streamer_name}, **Reporter:** {user.name}'
    )
    await unwanted_channel.send(message)

async def suche_spieler_in_api(api_url, gesuchter_spieler, interaction, api_key=None):
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict) and "result" in data and "stats" in data["result"]:
                    for spieler in data["result"]["stats"]:
                        if gesuchter_spieler in spieler['player'].lower():
                            message = f"Player: {spieler['player']}, Player ID: {spieler['player_id']}"
                            await interaction.followup.send(message, ephemeral=True)  # followup.send statt response.send_message
                            return True  # Spieler wurde gefunden, kehre mit True zurück
                return False  # Spieler wurde in dieser API nicht gefunden
            except ValueError:
                print(f"Fehler beim Verarbeiten der JSON-Daten von API: {api_url}")
                return False
        else:
            print(f"Fehlerhafte Antwort von API: {api_url}, Status Code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der API: {api_url}\n{str(e)}")
        return False


async def search_player_on_apis(player_name, interaction):
    player_found = False  # Überwacht, ob der Spieler gefunden wurde
    
    for api_url in api_urls:
        if "rcon.die-truemmertruppe.de" in api_url:
            found_in_api = await suche_spieler_in_api(api_url, player_name, interaction, api_key=api_key)  # Mit API-Key
        else:
            found_in_api = await suche_spieler_in_api(api_url, player_name, interaction)  # Ohne API-Key
        
        if found_in_api:  # Wenn der Spieler in einer API gefunden wurde
            player_found = True
    
    # Wenn der Spieler in keiner API gefunden wurde, verwende followup für die Antwort
    if not player_found:
        await interaction.followup.send("Player not found", ephemeral=True)



async def fetch_info_from_db(streamer_name):
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('SELECT steam_id, player_ingame_name, further_infos FROM streamers WHERE name = ?', (streamer_name,))
        result = cursor.fetchone()
        if result:
            return result[0], result[1], result[2]
        return None, None, None
    except sqlite3.Error as err:
        print(f"Error: {err}")
        return None, None, None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def get_twitch_token():
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()['access_token']

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
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()['data']

def create_or_update_table():
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS streamers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                status TEXT,
                steam_id TEXT,
                player_ingame_name TEXT,
                further_infos TEXT,
                last_updated TIMESTAMP,
                show_later_until TIMESTAMP
            )
        ''')
        
        # Check if column exists and add it if it doesn't
        cursor.execute('PRAGMA table_info(streamers)')
        columns = [col[1] for col in cursor.fetchall()]
        if 'player_ingame_name' not in columns:
            cursor.execute('ALTER TABLE streamers ADD COLUMN player_ingame_name TEXT')
            
        connection.commit()
    except sqlite3.Error as err:
        print(f"Error: {err}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def store_streamer_in_db(streamer_name, status=None, steam_id=None, player_ingame_name=None, further_infos=None):
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('SELECT status, steam_id, player_ingame_name, further_infos FROM streamers WHERE name = ?', (streamer_name,))
        result = cursor.fetchone()
        if result:
            existing_status, existing_steam_id, existing_player_ingame_name, existing_further_infos = result
            status = status or existing_status
            steam_id = steam_id or existing_steam_id
            player_ingame_name = player_ingame_name or existing_player_ingame_name
            further_infos = further_infos or existing_further_infos

        cursor.execute('''
            INSERT INTO streamers (name, status, steam_id, player_ingame_name, further_infos, last_updated, show_later_until)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(name) DO UPDATE SET
                status = excluded.status,
                steam_id = excluded.steam_id,
                player_ingame_name = excluded.player_ingame_name,
                further_infos = excluded.further_infos,
                last_updated = excluded.last_updated,
                show_later_until = NULL
        ''', (streamer_name, status, steam_id, player_ingame_name, further_infos, datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
        connection.commit()
    except sqlite3.Error as err:
        print(f"Error: {err}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def update_show_later(streamer_name, show_later_until):
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('''
            UPDATE streamers
            SET show_later_until = ?
            WHERE name = ?
        ''', (show_later_until, streamer_name))
        connection.commit()
    except sqlite3.Error as err:
        print(f"Error: {err}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def should_display_streamer(streamer_name):
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('SELECT status, last_updated, show_later_until FROM streamers WHERE name = ?', (streamer_name,))
        result = cursor.fetchone()
        status, last_updated = None, None
        if result:
            status, last_updated, show_later_until = result
            now = datetime.now()
            if show_later_until and now < datetime.strptime(show_later_until, "%Y-%m-%d %H:%M:%S.%f"):
                return False, status, last_updated
            if status == 'certify' and now - datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S.%f") < timedelta(days=CERTIFY_DAYS):
                return False, status, last_updated
            elif status in ['unwanted', 'irrelevant', 'console'] and now - datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S.%f") < timedelta(days=UNWANTED_DAYS):
                return False, status, last_updated
        return True, status, last_updated
    except sqlite3.Error as err:
        print(f"Error: {err}")
        return True, None, None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@tasks.loop(minutes=1)
async def check_streams():
    token = get_twitch_token()
    streamers = get_streamers(token)
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    online_streamers = set(streamer['user_name'] for streamer in streamers)
    current_time = datetime.now()
    for streamer_name, (message_id, last_seen) in list(reported_streamers.items()):
        if streamer_name not in online_streamers and current_time - last_seen > timedelta(minutes=DELETE_AFTER_ONLINE_TIME):
            try:
                message = await channel.fetch_message(message_id)
                await message.delete()
            except discord.NotFound:
                pass
            del reported_streamers[streamer_name]

    for streamer in streamers:
        display, status, last_updated = should_display_streamer(streamer['user_name'])
        if display and streamer['user_name'] not in reported_streamers:
            thumbnail_url = streamer['thumbnail_url'].replace("{width}", "320").replace("{height}", "180")
            stream_url = f"https://www.twitch.tv/{streamer['user_name']}"
            if status and last_updated:
                embed = discord.Embed(
                    title=f'**The known Streamer {streamer["user_name"]}** is now online',
                    description=f'**Last decision:** {status.capitalize()}, **Last Check on:** {last_updated.strftime("%d.%m.%Y")}',
                    url=stream_url
                )
                embed.set_image(url=thumbnail_url)
                message = await channel.send(embed=embed, view=MyView(streamer['user_name']))
            else:
                embed = discord.Embed(
                    title=f'A new Streamer **{streamer["user_name"]}** is now online',
                    url=stream_url
                )
                embed.set_image(url=thumbnail_url)
                message = await channel.send(embed=embed, view=MyView(streamer['user_name']))
            reported_streamers[streamer['user_name']] = (message.id, current_time)
            store_streamer_in_db(streamer['user_name'])
        else:
            if streamer['user_name'] in reported_streamers:
                reported_streamers[streamer['user_name']] = (reported_streamers[streamer['user_name']][0], current_time)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    create_or_update_table()
    await clear_channel_messages()
    check_streams.start()

async def clear_channel_messages():
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    await channel.purge(limit=None)

bot.run(DISCORD_TOKEN)
