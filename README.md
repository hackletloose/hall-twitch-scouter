# Hall Twitch Scouter

A bot to automatically monitor and report Twitch streamers playing *Hell Let Loose*. The bot fetches live streams from Twitch, filters streamers based on predefined rules, and sends reports to specific Discord channels. It also provides interactive features to mark streamers as unwanted, irrelevant, or certified, and includes auditing options.

## Features

- Fetches Twitch streams for *Hell Let Loose* in the selected language.
- Filters streamers based on custom rules (e.g., unwanted, irrelevant, console players).
- Posts streamers in Discord with interactive buttons for real-time moderation.
- Allows storing of streamer info, such as Steam ID and player in-game name.
- Supports unwanted reports directly in Discord.

## Prerequisites

Ensure you have the following installed:

- Python 3.8 or higher
- pip (Python package installer)
- SQLite3 (for the database)

### Ubuntu/Debian (APT Installation)

To install Python and other required dependencies:

```
bash
sudo apt update
sudo apt install python3 python3-pip python3-venv sqlite3 -y
```
### 1. Clone the Repository
```
git clone https://github.com/hackletloose/hall-twitch-scouter.git
cd hall-twitch-scouter
```
### 2. Set up the Virtual Environment
```
python3 -m venv venv
source venv/bin/activate  # For Linux/MacOS
# OR
venv\Scripts\activate  # For Windows
```
### 3. Install Dependencies
`pip install -r requirements.txt`

### 4. Setup .env
```
# Discord Setup
DISCORD_TOKEN=your_discord_token
REPORTS_DISCORD_CHANNEL_ID=your_reports_channel_id
UNWANTED_DISCORD_CHANNEL_ID=your_unwanted_channel_id

### Twitch Setup
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_CLIENT_SECRET=your_twitch_client_secret
STREAM_GAME_ID=497440  # Game ID for Hell Let Loose
STREAM_GAME_NAME=Hell Let Loose
STREAM_LANGUAGE=de  # Language filter for streams

# Bot Setup
CERTIFY_DAYS=90
UNWANTED_DAYS=180
IRRELEVANT_DAYS=180
CONSOLE_DAYS=180
HIDE_HOURS=6
DELETE_AFTER_ONLINE_TIME=15

# API URLs / API KEYs
API_URL_1=http://example.com:8010/api/get_live_scoreboard
API_URL_2=.../api/get_live_scoreboard
API_URL_3=.../api/get_live_scoreboard
API_URL_4=.../api/get_live_scoreboard
API_URL_5=.../api/get_live_scoreboard
API_URL_6=.../api/get_live_scoreboard
API_URL_7=.../api/get_live_scoreboard
API_URL_8=.../api/get_live_scoreboard
API_KEY_8=xxxx-xxxxx-xxxxxxxx-xxxxxxx-xxxxxx-xxxxxx
API_URL_9=.../api/get_live_scoreboard
API_URL_10=.../api/get_live_scoreboard
API_URL_11=.../api/get_live_scoreboard
API_URL_12=.../api/get_live_scoreboard
```
### 5. Setup the Database
The bot uses SQLite to store information about streamers. When the bot starts, it will automatically create a streamers.db database and set up the necessary tables.

### 6. Discord Bot Permissions
Ensure your Discord bot has the following permissions:
```
Read Messages
Send Messages
Manage Messages (for deleting outdated messages)
Use Slash Commands
Embed Links
```
### 7. Running the Bot
To start the bot, simply run:
`python bot.py`
