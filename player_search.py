import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from bin.connection_rcon import search_player_on_apis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("player_search_bot.log"),
        logging.StreamHandler()
    ]
)

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PLAYER_SEARCH_DISCORD_CHANNEL_ID = int(os.getenv('PLAYER_SEARCH_DISCORD_CHANNEL_ID'))

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
    logging.info(f"Clearing only the bot's messages in channel {PLAYER_SEARCH_DISCORD_CHANNEL_ID}.")
    channel = bot.get_channel(PLAYER_SEARCH_DISCORD_CHANNEL_ID)
    await channel.purge(limit=None, check=lambda m: m.author == bot.user)

@bot.event
async def on_ready():
    logging.info(f"Bot logged in as {bot.user}. Ready to search players!")
    channel = bot.get_channel(PLAYER_SEARCH_DISCORD_CHANNEL_ID)
    await clear_channel_messages()
    if channel:
        view = SearchView()
        await channel.send(
            "Mit dem folgenden Button könnt Ihr jeden derzeit aktiven Spieler suchen "
            "und herausfinden, auf welchem Server er unterwegs ist.",
            view=view
        )
        logging.info(f"Search button sent in channel {PLAYER_SEARCH_DISCORD_CHANNEL_ID}.")
    else:
        logging.error(f"Channel with ID {PLAYER_SEARCH_DISCORD_CHANNEL_ID} not found!")

def start_bot():
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    start_bot()
