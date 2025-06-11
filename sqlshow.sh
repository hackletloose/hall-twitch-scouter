#!/usr/bin/env bash

# Passe diese Variablen nach Bedarf an oder trage sie direkt in .env ein
HOST="127.0.0.1"
PORT="3306"
DBNAME="hackletloose"
USER="hackletloose"
PASSWORD="Jammerlappen"
TABLENAME="HaLL_twitch_scouter"

# Hier wird die Tabelle in der Konsole ausgegeben, ohne dass du ein Passwort eingeben musst.
# Beachte, dass das Passwort im Klartext im Skript steht und somit nicht sicher ist.
mysql -h "$HOST" -P "$PORT" -u "$USER" -p"$PASSWORD" \
  -D "$DBNAME" \
  -e "SELECT * FROM $TABLENAME;"
