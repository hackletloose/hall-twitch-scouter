# Hall Twitch Scouter

A bot to automatically monitor and report Twitch streamers playing *Hell Let Loose*. The bot fetches live streams from Twitch, filters streamers based on predefined rules, and sends reports to specific Discord channels. It also provides interactive features to mark streamers as unwanted, irrelevant, or certified, and includes auditing options.

## Features

- Fetches Twitch streams for *Hell Let Loose* in the selected language.
- Filters streamers based on custom rules (e.g., unwanted, irrelevant, console players).
- Posts streamers in Discord with interactive buttons for real-time moderation.
- Allows storing of streamer info, such as Steam ID and player in-game name.
- Supports unwanted reports directly in Discord.

ToDo:
Execute the following commands after downloading:
1. Copy the `.env.dist` file to `.env` and enter your values.
2. Run the command `pip install python-dotenv discord.py requests python-dotenv mysql-connector-python`.
3. Copy `twitch-scouter.service.dist` to `/etc/systemd/system/twitch-scouter.service`
4. Activate and start the service with `sudo systemctl enable twitch-scouter.service` and `sudo systemctl start twitch-scouter.service`.

## Prerequisites

Ensure you have the following installed:

- Python 3.8 or higher
- pip (Python package installer)
- MariaDB Client (for the database connection)
- MariaDB Server (for the database)

### Ubuntu/Debian (APT Installation)

To install Python and other required dependencies:

```
bash
sudo apt update
sudo apt install python3 python3-pip libmysqlclient-dev build-essential -y

```
### 1. Clone the Repository
```
git clone https://github.com/hackletloose/hall-twitch-scouter.git
cd hall-twitch-scouter
```
### 2. Set up the Virtual Environment (OPTIONAL!)
```
sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate  # For Linux/MacOS
# OR
venv\Scripts\activate  # For Windows
```
### 3. Install Dependencies
`pip install -r requirements.txt`

### 4. Setup .env
```
#DISCORD SETTINGS (nessassary for show up streamers and categorizing them)
DISCORD_TOKEN=
REPORTS_DISCORD_CHANNEL_ID=
UNWANTED_DISCORD_CHANNEL_ID=

#TWITCH API SETTINGS (nessassary for show up streamers)
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_CLIENT_SECRET=your_twitch_client_secret
STREAM_GAME_ID=497440  # Game ID for Hell Let Loose
STREAM_LANGUAGE=de  # Language filter for streams

#SCRIPT VARIABLES (used for shown and unshown streamers)
CERTIFY_DAYS=90
UNWANTED_DAYS=180
IRRELEVANT_DAYS=180
CONSOLE_DAYS=180
HIDE_HOURS=6
DELETE_AFTER_ONLINE_TIME=15
DATABASE_PATH=./data/streamers.db

#DATABASE VARIABLES (used for saving streamers data)
DATABASE_HOST=
DATABASE_PORT=3306
DATABASE_NAME=
DATABASE_USER=
DATABASE_PASSWORD=

# YOUR KNOWN CRCON APIS (for the search button)
API_URL_1=
API_KEY_1=
API_URL_2=
API_KEY_2=
API_URL_3=
API_KEY_3=
API_URL_4=
API_KEY_4=
# You could add more and more API_URL_x and API_KEY_x to this configuration.
```
### 5. Setup the Database
The bot uses MariaDB to store information about streamers. When the bot starts, it will automatically create a streamers.db database and set up the necessary tables.

### 6. Discord Bot Permissions
Ensure your Discord bot has the following permissions:
```
Read Messages
Send Messages
Manage Messages (for deleting outdated messages)
Use Slash Commands
Embed Links
```
### 7. Data migration
If you did use this system before, you now have to migrate the SQLite Database to MariaDB Database. For this, please use the Migration by running `python v3_data_migration.py`

### 8. Running the Bot
To start the bot, simply run:
`python twitch-scouter.py`
