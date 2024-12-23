import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from bin.connection_rcon import search_player_on_apis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("player_search_bot.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PLAYER_SEARCH_DISCORD_CHANNEL_ID = int(os.getenv('PLAYER_SEARCH_DISCORD_CHANNEL_ID'))  # Get the channel ID from .env

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents, reconnect=True)

class SearchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🔍 Search Player', style=discord.ButtonStyle.primary, custom_id='search_player_button')
    async def search_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        logging.info(f"{interaction.user.name} initiated player search.")
        await interaction.response.send_modal(PlayerSearchModal())

class PlayerSearchModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title='Search Player')
        self.player_name_input = discord.ui.TextInput(
            label='Player Name',
            placeholder='Enter the player name or part of the name',
            custom_id='player_name_input',
            required=True
        )
        self.add_item(self.player_name_input)

    async def on_submit(self, interaction: discord.Interaction):
        player_name = self.player_name_input.value.lower()
        logging.info(f"Searching for player: {player_name}.")
        await interaction.response.send_message(f'Searching for "{player_name}"...', ephemeral=True)
        await search_player_on_apis(player_name, interaction)

async def clear_channel_messages():
    logging.info(f"Clearing all messages in channel {PLAYER_SEARCH_DISCORD_CHANNEL_ID}.")
    channel = bot.get_channel(PLAYER_SEARCH_DISCORD_CHANNEL_ID)
    await channel.purge(limit=None)

@bot.event
async def on_ready():
    logging.info(f"Bot logged in as {bot.user}. Ready to search players!")

    # Automatically send the search button in the specified channel
    channel = bot.get_channel(PLAYER_SEARCH_DISCORD_CHANNEL_ID)
    await clear_channel_messages()
    if channel:
        view = SearchView()
        await channel.send("Click the button below to search for a player.", view=view)
        logging.info(f"Search button sent in channel {PLAYER_SEARCH_DISCORD_CHANNEL_ID}.")
    else:
        logging.error(f"Channel with ID {PLAYER_SEARCH_DISCORD_CHANNEL_ID} not found!")

def start_bot():
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    start_bot()
