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
    fetch_info_from_db,
    fetch_status_from_db
)
from bin.connection_rcon import (
    search_player_on_apis
)

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

    async def setup_buttons(self, status):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "unwanted_button_id":
                if status == "unwanted" or status == "2nd warn":
                    child.label = "👎 unwanted"
                elif status == "1st warn":
                    child.label = "👎 2nd warn"
                else:
                    child.label = "👎 1st warn"
                break

    @discord.ui.button(label="👀 Start/Stop audit", style=discord.ButtonStyle.primary, custom_id="watch_button_id")
    async def watch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.watching:
            self.watching = True
            await interaction.response.send_message(f'**{interaction.user.name}** is now watching the stream of **{self.streamer_name}**.')
            logging.info(f"{interaction.user.name} is watching {self.streamer_name}'s stream.")
        else:
            self.watching = False
            await interaction.response.send_message(f'**{interaction.user.name}** has left the stream of **{self.streamer_name}**.')
            logging.info(f"{interaction.user.name} stopped watching {self.streamer_name}'s stream.")

    @discord.ui.button(label="👎", style=discord.ButtonStyle.danger, custom_id="unwanted_button_id")
    async def unwanted(self, interaction: discord.Interaction, button: discord.ui.Button):
        logging.info(f"{interaction.user.name} clicked 'unwanted' for streamer {self.streamer_name}.")
        modal = await CategorizeModal.create("unwanted", self.streamer_name)
        await interaction.response.send_modal(modal)
        try:
            modal_interaction = await interaction.client.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == modal.custom_id and i.user.id == interaction.user.id,
                timeout=None,
            )
            steam_id = modal_interaction.data.get("steam_id_input")
            player_ingame_name = modal_interaction.data.get("player_ingame_name_input")
            further_infos = modal_interaction.data.get("further_infos_input")
            db_status = await fetch_status_from_db(self.streamer_name)
            await send_unwanted_report(
                modal_interaction.user,
                self.streamer_name,
                steam_id,
                player_ingame_name,
                further_infos,
                db_status
            )
        except asyncio.TimeoutError:
            logging.warning(f"Modal submission timed out for {self.streamer_name}.")

    @discord.ui.button(label="👍 certify", style=discord.ButtonStyle.success, custom_id="certify_button_id")
    async def certify(self, interaction: discord.Interaction, button: discord.ui.Button):
        logging.info(f"Certifying {self.streamer_name} by {interaction.user.name}.")
        await interaction.response.send_modal(await CategorizeModal.create("certify", self.streamer_name))

    @discord.ui.button(label="👋🎮 irrelevant", style=discord.ButtonStyle.primary, custom_id="irrelevant_button_id")
    async def irrelevant(self, interaction: discord.Interaction, button: discord.ui.Button):
        store_streamer_in_db(self.streamer_name, status="irrelevant")
        logging.info(f"{interaction.user.name} marked {self.streamer_name} as irrelevant.")
        await interaction.response.send_message(f'{interaction.user.name}: Streamer **{self.streamer_name}** has been marked as **irrelevant**.')

    @discord.ui.button(label="⏰ display later", style=discord.ButtonStyle.secondary, custom_id="show_later_button_id")
    async def show_later(self, interaction: discord.Interaction, button: discord.ui.Button):
        show_later_until = datetime.now() + timedelta(hours=HIDE_HOURS)
        update_show_later(self.streamer_name, show_later_until)
        logging.info(f"{interaction.user.name} requested to hide {self.streamer_name} for {HIDE_HOURS} hours.")
        await interaction.response.send_message(f'{interaction.user.name}: Streamer **{self.streamer_name}** will not be shown again for **{HIDE_HOURS} hours**')

    @discord.ui.button(label="🔍 search", style=discord.ButtonStyle.secondary, custom_id="search_player_button_id")
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
        super().__init__(title=f'{action.capitalize()} Streamer', custom_id=f"{action}_modal")
        self.action = action
        self.streamer_name = streamer_name

        self.steam_id_input = discord.ui.TextInput(
            label='Player-ID',
            placeholder='Please enter XBOX or Steam-ID',
            custom_id="steam_id_input",
            default=steam_id or '',
            required=False
        )
        self.add_item(self.steam_id_input)

        if action == 'unwanted':
            self.player_ingame_name_input = discord.ui.TextInput(
                label='Player Ingame Name',
                placeholder='Please enter player ingame name',
                custom_id="player_ingame_name_input",
                default=player_ingame_name or '',
                max_length=255,
                required=False
            )
            self.further_infos_input = discord.ui.TextInput(
                label='Additional Information',
                placeholder='Enter additional information',
                custom_id="further_infos_input",
                default=further_infos or '',
                max_length=255,
                required=False
            )
            self.add_item(self.player_ingame_name_input)
            self.add_item(self.further_infos_input)

    @classmethod
    async def create(cls, action, streamer_name):
        _, steam_id, player_ingame_name, further_infos = await asyncio.to_thread(fetch_info_from_db, streamer_name)
        logging.info(f"Fetched info from DB for {streamer_name}.")
        return cls(action, streamer_name, steam_id=steam_id, player_ingame_name=player_ingame_name, further_infos=further_infos)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            steam_id = self.steam_id_input.value
            player_ingame_name = self.player_ingame_name_input.value if self.action == 'unwanted' else None
            further_infos = self.further_infos_input.value if self.action == 'unwanted' else None
            db_status = await fetch_status_from_db(self.streamer_name)
            await asyncio.to_thread(
                store_streamer_in_db,
                self.streamer_name,
                status=self.action,
                steam_id=steam_id,
                player_ingame_name=player_ingame_name,
                further_infos=further_infos,
                update_last_updated=True
            )
            await send_unwanted_report(
                interaction.user,
                self.streamer_name,
                steam_id,
                player_ingame_name,
                further_infos,
                db_status
            )
            await interaction.response.send_message(
                f"Successfully submitted the report for {self.streamer_name} as '{self.action}'."
            )
        except Exception as e:
            logging.error(f"Error processing modal submission: {e}")
            await interaction.response.send_message(
                f"An error occurred while processing your submission: {e}",
                ephemeral=True
            )

async def on_submit(self, interaction: discord.Interaction):
    steam_id = self.steam_id_input.value
    player_ingame_name = self.player_ingame_name_input.value if self.action == 'unwanted' else None
    further_infos = self.further_infos_input.value if self.action == 'unwanted' else None
    db_steam_id, db_player_ingame_name, db_further_infos = await asyncio.to_thread(fetch_info_from_db, self.streamer_name)

    if db_steam_id or db_player_ingame_name or db_further_infos:
        message = (
            f'**{interaction.user.name}** decision: **{self.streamer_name}** (bekannter Streamer) marked as **{self.action}**.\n\n'
            f'**Status:** {self.action}\n'
            f'**Player-ID:** {db_steam_id or "Nicht angegeben"}\n'
            f'**Player Name:** {db_player_ingame_name or "Nicht angegeben"}\n'
            f'**Weitere Informationen:** {db_further_infos or "Keine"}'
        )
    else:
        message = (
            f'**{interaction.user.name}** decision: **{self.streamer_name}** (neuer Streamer) marked as **{self.action}**.'
        )
    await asyncio.to_thread(store_streamer_in_db, self.streamer_name, status=self.action, steam_id=steam_id, player_ingame_name=player_ingame_name, further_infos=further_infos, update_last_updated=True)
    logging.info(f"Stored {self.streamer_name} in DB with status {self.action} by {interaction.user.name}.")
    await interaction.response.send_message(message)

async def send_unwanted_report(user, streamer_name, steam_id, player_ingame_name, further_infos, status):
    if status == "1st warn":
        channel_id = int(os.getenv("2ND_WARN_DISCORD_CHANNEL_ID"))
        warnung = f"Second Warning - tempban: {int(os.getenv('2ND_WARN_HIDE_HOURS'))}h"
    elif status == "2nd warn" or status == "unwanted":
        channel_id = int(os.getenv("UNWANTED_DISCORD_CHANNEL_ID"))
        warnung = "All Warnings ignored - permaban"
    else:
        channel_id = int(os.getenv("1ST_WARN_DISCORD_CHANNEL_ID"))
        warnung = f"Second Warning - tempban: {int(os.getenv('1ST_WARN_HIDE_HOURS'))}h"
        await user.send(f"Unknown status: {status}. Report not sent.")
        logging.error(f"Unknown status for streamer {streamer_name}: {status}.")
        return

    channel = discord.utils.get(user.guild.channels, id=channel_id)
    if not channel:
        await user.send(f"Could not find the report channel for status '{status}'. Please check the configuration.")
        logging.error(f"Could not find channel for status '{status}' for {streamer_name}.")
        return

    message = (
        f'**Name:** {player_ingame_name}\n'
        f'**SteamID:** {steam_id}\n'
        f'**Steam-Profile:** https://steamcommunity.com/profiles/{steam_id}\n'
        f'**Issue:** Streaming without map overlay or delay, warnings: {warnung}, further info: {further_infos}, '
        f'Twitch URL: https://twitch.tv/{streamer_name}, Reporter: {user.name}'
    )
    try:
        await channel.send(message)
        logging.info(f"Report for {streamer_name} sent to channel {channel.name} ({channel.id}).")
    except discord.Forbidden:
        await user.send(f"I do not have permission to send messages in the channel for status '{status}'.")
        logging.error(f"Permission denied to send report in channel for status '{status}' for {streamer_name}.")
    except discord.HTTPException as http_err:
        await user.send(f"Failed to send report due to an HTTP error: {http_err}")
        logging.error(f"HTTP error occurred while sending report for {streamer_name}: {http_err}.")
    except Exception as e:
        await user.send(f"An unexpected error occurred while trying to send the report: {e}")
        logging.error(f"Unexpected error occurred while sending report for {streamer_name}: {e}.")

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
