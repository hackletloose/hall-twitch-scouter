import discord
from discord.ext import tasks, commands
import requests
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import time
from bin.connection_mariadb import (
    create_or_update_table,
    store_streamer_in_db,
    fetch_info_from_db,
    update_show_later,
    should_display_streamer,
    delete_expired_streamers,
    delete_old_streamers
)
from bin.connection_twitch import (
    get_twitch_token,
    get_streamers
)
from bin.connection_discord import (
    MyView,
    CategorizeModal,
    PlayerSearchModal,
    send_unwanted_report,
    start_bot
)

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('REPORTS_DISCORD_CHANNEL_ID'))
DELETE_AFTER_ONLINE_TIME = int(os.getenv('DELETE_AFTER_ONLINE_TIME'))
CERTIFY_DAYS = int(os.getenv('CERTIFY_DAYS'))
UNWANTED_DAYS = int(os.getenv('UNWANTED_DAYS'))
IRRELEVANT_DAYS = int(os.getenv('IRRELEVANT_DAYS'))

reported_streamers = {}
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, reconnect=True)

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
        display, status, last_updated = should_display_streamer(streamer['user_name'], CERTIFY_DAYS, UNWANTED_DAYS, IRRELEVANT_DAYS)
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
            await asyncio.to_thread(store_streamer_in_db, streamer['user_name'])
        else:
            if streamer['user_name'] in reported_streamers:
                reported_streamers[streamer['user_name']] = (reported_streamers[streamer['user_name']][0], current_time)

@tasks.loop(minutes=60)
async def database_cleanup():
    await asyncio.to_thread(delete_expired_streamers)
    await asyncio.to_thread(delete_old_streamers)

@bot.event
async def on_ready():
    try:
        await asyncio.to_thread(create_or_update_table)
        if not database_cleanup.is_running():
            database_cleanup.start()
        await clear_channel_messages()
        if not check_streams.is_running():
            check_streams.start()
        print(f'Logged in as {bot.user.name}')
    except Exception as e:
        print(f"Error during on_ready: {e}")

async def on_disconnect():
    print("Bot disconnected. Attempting to reconnect...")

async def clear_channel_messages():
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    await channel.purge(limit=None)

bot.run(DISCORD_TOKEN)
