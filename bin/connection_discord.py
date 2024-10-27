import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import asyncio
import time
import logging
from bin.connection_mariadb import (
    store_streamer_in_db,
    update_show_later,
    fetch_info_from_db
)
from bin.connection_rcon import (
    search_player_on_apis
)

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("connection_discord.log"),
        logging.StreamHandler()
    ]
)

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
HIDE_HOURS = int(os.getenv('HIDE_HOURS'))
UNWANTED_CHANNEL_ID = int(os.getenv('UNWANTED_DISCORD_CHANNEL_ID'))
CONSOLE_DAYS = int(os.getenv('CONSOLE_DAYS'))

class MyView(discord.ui.View):
    def __init__(self, streamer_name):
        super().__init__(timeout=None)
        self.streamer_name = streamer_name
        self.watching = False
    
    @discord.ui.button(label='👀 Start/Stop audit', style=discord.ButtonStyle.primary, custom_id='watch_button_id')
    async def watch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.watching:
            self.watching = True
            await interaction.response.send_message(f'**{interaction.user.name}** is now watching the stream of **{self.streamer_name}**.')
            logging.info(f"{interaction.user.name} is watching {self.streamer_name}'s stream.")
        else:
            self.watching = False
            await interaction.response.send_message(f'**{interaction.user.name}** has left the stream of **{self.streamer_name}**.')
            logging.info(f"{interaction.user.name} stopped watching {self.streamer_name}'s stream.")

    @discord.ui.button(label='👎 unwanted', style=discord.ButtonStyle.danger, custom_id='unwanted_button_id')
    async def unwanted(self, interaction: discord.Interaction, button: discord.ui.Button):
        logging.info(f"Marking {self.streamer_name} as unwanted by {interaction.user.name}.")
        await interaction.response.send_modal(await CategorizeModal.create('unwanted', self.streamer_name))

    @discord.ui.button(label='👍 certify', style=discord.ButtonStyle.success, custom_id='certify_button_id')
    async def certify(self, interaction: discord.Interaction, button: discord.ui.Button):
        logging.info(f"Certifying {self.streamer_name} by {interaction.user.name}.")
        await interaction.response.send_modal(await CategorizeModal.create('certify', self.streamer_name))

    @discord.ui.button(label='👋🎮 irrelevant', style=discord.ButtonStyle.primary, custom_id='irrelevant_button_id')
    async def irrelevant(self, interaction: discord.Interaction, button: discord.ui.Button):
        store_streamer_in_db(self.streamer_name, status='irrelevant')
        logging.info(f"{interaction.user.name} marked {self.streamer_name} as irrelevant.")
        await interaction.response.send_message(f'{interaction.user.name}: Streamer **{self.streamer_name}** has been marked as **irrelevant**.')

    @discord.ui.button(label='⏰ display later', style=discord.ButtonStyle.secondary, custom_id='show_later_button_id')
    async def show_later(self, interaction: discord.Interaction, button: discord.ui.Button):
        show_later_until = datetime.now() + timedelta(hours=HIDE_HOURS)
        update_show_later(self.streamer_name, show_later_until)
        logging.info(f"{interaction.user.name} requested to hide {self.streamer_name} for {HIDE_HOURS} hours.")
        await interaction.response.send_message(f'{interaction.user.name}: Streamer **{self.streamer_name}** will not be shown again for **{HIDE_HOURS} hours**')

    @discord.ui.button(label='🔍 search', style=discord.ButtonStyle.secondary, custom_id='search_player_button_id')
    async def search_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        logging.info(f"{interaction.user.name} initiated player search.")
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
        logging.info(f"Searching for player: {player_name}.")
        await interaction.response.send_message(f'Searching for "{player_name}"...', ephemeral=True)
        await search_player_on_apis(player_name, interaction) 

class CategorizeModal(discord.ui.Modal):
    def __init__(self, action, streamer_name, steam_id=None, player_ingame_name=None, further_infos=None):
        super().__init__(title=f'{action.capitalize()} Streamer')
        self.action = action
        self.streamer_name = streamer_name
        self.steam_id_input = discord.ui.TextInput(
            label='Player-ID',
            placeholder='Please enter XBOX or Steam-ID',
            custom_id=f'steam_id_input_{action}_{streamer_name}',
            default=steam_id or '',
            required=False
        )
        self.add_item(self.steam_id_input)
        if action == 'unwanted':
            self.player_ingame_name_input = discord.ui.TextInput(
                label='Player Ingame Name',
                placeholder='Please enter player ingame name',
                custom_id=f'player_ingame_name_input_{action}_{streamer_name}',
                default=player_ingame_name or '',
                max_length=255,
                required=False
            )
            self.further_infos_input = discord.ui.TextInput(
                label='Additional Information',
                placeholder='Enter additional information',
                custom_id=f'further_infos_input_{action}_{streamer_name}',
                default=further_infos or '',
                max_length=255,
                required=False
            )
            self.add_item(self.player_ingame_name_input)
            self.add_item(self.further_infos_input)

    @classmethod
    async def create(cls, action, streamer_name):
        steam_id, player_ingame_name, further_infos = await asyncio.to_thread(fetch_info_from_db, streamer_name)
        logging.info(f"Fetched info from DB for {streamer_name}.")
        return cls(action, streamer_name, steam_id=steam_id, player_ingame_name=player_ingame_name, further_infos=further_infos)

    async def on_submit(self, interaction: discord.Interaction):
        steam_id = self.steam_id_input.value
        player_ingame_name = self.player_ingame_name_input.value if self.action == 'unwanted' else None
        further_infos = self.further_infos_input.value if self.action == 'unwanted' else None
        await asyncio.to_thread(store_streamer_in_db, self.streamer_name, status=self.action, steam_id=steam_id, player_ingame_name=player_ingame_name, further_infos=further_infos)
        logging.info(f"Stored {self.streamer_name} in DB with status {self.action} by {interaction.user.name}.")
        
        if self.action == 'unwanted':
            await asyncio.to_thread(send_unwanted_report, interaction.user, self.streamer_name, steam_id, player_ingame_name, further_infos)
            await interaction.response.send_message(f'**{interaction.user.name}** decision: **{self.streamer_name}** with Player-ID **{steam_id}**, Ingame Name **{player_ingame_name}**, and Infos **{further_infos}** marked as **{self.action}**.')
        else:
            await interaction.response.send_message(f'**{interaction.user.name}** decision: **{self.streamer_name}** marked as **{self.action}**.')

async def send_unwanted_report(user, streamer_name, steam_id, player_ingame_name, further_infos):
    unwanted_channel = discord.utils.get(user.guild.channels, id=int(UNWANTED_CHANNEL_ID))
    if unwanted_channel is None:
        await user.send(f"Could not find the 'unwanted' report channel. Please check the configuration.")
        logging.error(f"Could not find 'unwanted' channel for {streamer_name}.")
        return
    message = (
        f'**Name:** {player_ingame_name}\n'
        f'**SteamID:** {steam_id}\n'
        f'**Steam-Profile:** https://steamcommunity.com/profiles/{steam_id}\n'
        f'**Issue:** Streaming without map overlay or delay, further info: {further_infos}, Twitch URL: https://twitch.tv/{streamer_name}, Reporter: {user.name}'
    )

    try:
        await unwanted_channel.send(message)
        logging.info(f"Unwanted report sent for {streamer_name}.")
    except discord.Forbidden:
        await user.send(f"I do not have permission to send messages in the 'unwanted' report channel. Please check my permissions.")
        logging.error(f"Permission denied to send report in 'unwanted' channel for {streamer_name}.")
    except discord.HTTPException as http_err:
        await user.send(f"Failed to send unwanted report due to an HTTP error: {http_err}")
        logging.error(f"HTTP error occurred while sending unwanted report for {streamer_name}: {http_err}.")
    except Exception as e:
        await user.send(f"An unexpected error occurred while trying to send the report: {e}")
        logging.error(f"Unexpected error occurred while sending unwanted report for {streamer_name}: {e}.")

def start_bot():
    while True:
        try:
            logging.info("Starting bot...")
            bot.run(DISCORD_TOKEN)
        except (discord.errors.ConnectionClosed, discord.errors.GatewayNotFound) as e:
            logging.error(f"Connection error occurred: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logging.error(f"Unexpected error: {e}. Restarting bot...")
            time.sleep(10)

if __name__ == "__main__":
    start_bot()
