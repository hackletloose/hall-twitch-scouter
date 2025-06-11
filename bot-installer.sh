#!/bin/bash
set -e

# Usage-Hinweis, falls kein Parameter übergeben wurde
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 [install|uninstall|reinstall]"
  exit 1
fi

TRIGGER="$1"

# Farben definieren
YELLOW='\e[1;33m'
GREEN='\e[1;32m'
NC='\e[0m'  # No Color

# Funktion, um die .env Datei zu prüfen bzw. bei Bedarf anzulegen und zu editieren.
# Das Script bricht ab, wenn an der .env keine Änderungen vorgenommen werden.
check_env() {
  if [ ! -f ".env" ]; then
    if [ -f ".env.dist" ]; then
      cp .env.dist .env
      echo "Eine Vorlage (.env.dist) wurde als .env angelegt."
      read -p "Drücken Sie Enter, um .env in nano zu öffnen und anzupassen..."
      old_hash=$(md5sum .env | awk '{print $1}')
      nano .env
      new_hash=$(md5sum .env | awk '{print $1}')
      if [ "$old_hash" = "$new_hash" ]; then
        echo "Die .env Datei wurde nicht geändert. Installation wird abgebrochen."
        exit 1
      fi
    elif [ -f "dist.env" ]; then
      cp dist.env .env
      echo "Eine Vorlage (dist.env) wurde als .env angelegt."
      read -p "Drücken Sie Enter, um .env in nano zu öffnen und anzupassen..."
      old_hash=$(md5sum .env | awk '{print $1}')
      nano .env
      new_hash=$(md5sum .env | awk '{print $1}')
      if [ "$old_hash" = "$new_hash" ]; then
        echo "Die .env Datei wurde nicht geändert. Installation wird abgebrochen."
        exit 1
      fi
    else
      echo "Keine .env Datei oder Vorlage (.env.dist/dist.env) gefunden."
      echo "Bitte erstellen Sie eine .env Datei mit den erforderlichen Konfigurationen."
      exit 1
    fi
  else
    echo -e "${YELLOW}Aktuelle .env Datei:${NC}"
    echo -e "${GREEN}"
    cat .env
    echo -e "${NC}"
    read -p "Ist Ihre .env Datei korrekt konfiguriert? (J/N) " ans
    if [[ "$ans" =~ ^[Nn] ]]; then
      old_hash=$(md5sum .env | awk '{print $1}')
      nano .env
      new_hash=$(md5sum .env | awk '{print $1}')
      if [ "$old_hash" = "$new_hash" ]; then
        echo "Die .env Datei wurde nicht geändert. Installation wird abgebrochen."
        exit 1
      fi
    fi
  fi
}

# Funktion, um zu prüfen, ob der Bot bereits eingeladen wurde und die notwendigen Rechte hat
check_bot_invite() {
  if [ -f ".discord-bot-invite" ]; then
    echo -e "${YELLOW}Einladungs-URL für den Discord-Bot:${NC}"
    echo -e "${GREEN}"
    cat .discord-bot-invite
    echo -e "${NC}"
    read -p "Wurden der Bot eingeladen und die notwendigen Rechte (z. B. auf die relevanten Kanäle) vergeben? (J/N) " invite_ans
    if [[ ! "$invite_ans" =~ ^[Jj] ]]; then
      echo "Bitte laden Sie den Bot ein und konfigurieren Sie die Rechte, bevor Sie fortfahren."
      exit 1
    fi
  else
    echo "Keine Einladungs-URL (.discord-bot-invite) gefunden. Bitte legen Sie diese Datei an."
    exit 1
  fi
}

# Funktion für die Installation
install_bot() {
  # Vor Installation: .env prüfen/erstellen und ggf. editieren
  check_env

  # Prüfe, ob der Bot bereits eingeladen und richtig konfiguriert ist
  check_bot_invite

  # Prüfe, ob das Skript als root (oder mit sudo) ausgeführt wird
  if [ "$EUID" -ne 0 ]; then
    echo "Bitte führen Sie das Skript als root oder mit sudo aus."
    exit 1
  fi

  # Bestimme den Nutzer, unter dem der Bot-Dienst laufen soll
  if [ -n "$SUDO_USER" ]; then
    RUN_USER=$SUDO_USER
  else
    RUN_USER=$(whoami)
  fi

  echo "Prüfe Python 3.12 und notwendige Pakete..."
  if ! command -v python3.12 &> /dev/null; then
    apt-get update
    apt-get install -y python3.12 python3.12-venv python3.12-full python3.12-dev
  else
    echo "Python 3.12 ist bereits installiert."
  fi

  # Erstelle im aktuellen Verzeichnis eine virtuelle Umgebung (Ordner: venv)
  if [ ! -d "venv" ]; then
    echo "Erstelle virtuelle Umgebung..."
    python3.12 -m venv venv
  else
    echo "Virtuelle Umgebung existiert bereits."
  fi

  # Aktiviere die virtuelle Umgebung und installiere die Anforderungen (Ausgabe nur bei Fehlern)
  echo "Installiere Python-Pakete aus requirements.txt..."
  source venv/bin/activate
  pip install --upgrade pip > /dev/null 2>&1 || { echo "Fehler beim Aktualisieren von pip."; exit 1; }
  pip install -r requirements.txt > /dev/null 2>&1 || { echo "Fehler beim Installieren der Anforderungen."; exit 1; }
  deactivate

  CUR_DIR=$(pwd)
  BASE_NAME=$(basename "$CUR_DIR")

  # Erstelle den systemd-Dienst für den Bot
  echo "Erstelle systemd Service für den Bot..."
  cat <<EOF > /etc/systemd/system/${BASE_NAME}.service
[Unit]
Description=Discord Bot Service for ${BASE_NAME}
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${CUR_DIR}
ExecStart=${CUR_DIR}/venv/bin/python ${CUR_DIR}/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

  # Erstelle den systemd-Dienst für wöchentliche Pip-Updates (Neustart des Bot-Dienstes nach Update)
  echo "Erstelle systemd Service für wöchentliche Pip-Updates..."
  cat <<EOF > /etc/systemd/system/${BASE_NAME}_update.service
[Unit]
Description=Weekly update of pip packages for ${BASE_NAME}

[Service]
Type=oneshot
WorkingDirectory=${CUR_DIR}
ExecStart=/bin/bash -c "sudo -u ${RUN_USER} ${CUR_DIR}/venv/bin/pip install -r requirements.txt > /dev/null 2>&1 && systemctl restart ${BASE_NAME}.service"
EOF

  # Erstelle den systemd-Timer für wöchentliche Pip-Updates
  echo "Erstelle systemd Timer für wöchentliche Pip-Updates..."
  cat <<EOF > /etc/systemd/system/${BASE_NAME}_update.timer
[Unit]
Description=Run ${BASE_NAME}_update.service weekly

[Timer]
OnBootSec=10min
OnUnitActiveSec=1w
Persistent=true

[Install]
WantedBy=timers.target
EOF

  echo "Lade systemd Konfiguration neu und starte Dienste..."
  systemctl daemon-reload
  systemctl enable ${BASE_NAME}.service
  systemctl start ${BASE_NAME}.service
  systemctl enable ${BASE_NAME}_update.timer
  systemctl start ${BASE_NAME}_update.timer

  echo -e "${GREEN}Installation abgeschlossen. Der Bot (${BASE_NAME}) läuft nun als Dienst und wird bei Systemstart gestartet.${NC}"
}

# Funktion für das Entfernen der Dienste und des venv-Verzeichnisses
uninstall_bot() {
  if [ "$EUID" -ne 0 ]; then
    echo "Bitte führen Sie das Skript als root oder mit sudo aus."
    exit 1
  fi

  CUR_DIR=$(pwd)
  BASE_NAME=$(basename "$CUR_DIR")

  echo "Stoppe und deaktiviere den Bot-Dienst..."
  systemctl stop ${BASE_NAME}.service || true
  systemctl disable ${BASE_NAME}.service || true
  systemctl stop ${BASE_NAME}_update.timer || true
  systemctl disable ${BASE_NAME}_update.timer || true

  echo "Entferne die systemd Dateien..."
  rm -f /etc/systemd/system/${BASE_NAME}.service
  rm -f /etc/systemd/system/${BASE_NAME}_update.service
  rm -f /etc/systemd/system/${BASE_NAME}_update.timer

  echo "Lade systemd Konfiguration neu..."
  systemctl daemon-reload

  if [ -d "venv" ]; then
    echo "Lösche das venv-Verzeichnis..."
    rm -rf venv
  fi

  echo "Uninstallation abgeschlossen. Dienste und venv wurden entfernt."
}

# Funktion für Reinstallation: zuerst deinstallieren, dann installieren
reinstall_bot() {
  uninstall_bot
  install_bot
}

case "$TRIGGER" in
  install)
    install_bot
    ;;
  uninstall)
    uninstall_bot
    ;;
  reinstall)
    reinstall_bot
    ;;
  *)
    echo "Ungültiger Trigger. Bitte benutzen Sie einen der folgenden: install, uninstall, reinstall"
    exit 1
    ;;
esac

