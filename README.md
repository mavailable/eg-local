# EG Local — Casino / Escape Game (RFID + MQTT)

**Version:** 1.0 — 23 août 2025

## Démarrage rapide

```bash
# 1) Infra
docker compose up -d
# Core: http://localhost:8000/health

# 2) Agent slot (mode dev clavier)
cd agents/slot
python3 -m pip install paho-mqtt pyyaml
python3 slot_agent.py device_config.yaml
# r 04A37C91 / balance / b / c / v A

# 3) UIs (en mode dev local)
cd ui/slot && npm i && npm run dev      # http://localhost:5173/?id=slot-01
cd ui/change && npm i && npm run dev    # http://localhost:5174/?id=change-01
cd ui/operator && npm i && npm run dev  # http://localhost:5175/

# Pour kiosk RPi: voir section "Déploiement RPi" ci-dessous
```

## Endpoints opérateur

```bash
curl -X POST http://localhost:8000/api/mode -H 'content-type: application/json' -d '{"mode":"night"}'
curl -X POST http://localhost:8000/api/night/step -H 'content-type: application/json' -d '{"step":1,"question":"Choix ?","options":["A","B","C"]}'
curl http://localhost:8000/api/payouts
```

## Tests T1–T11 (scripts)

```bash
./scripts/smoke_test.sh
./scripts/seed_payout.sh
```

## Déploiement RPi (agents + kiosk)

### Guide de déploiement d'une machine Slot

#### Prérequis système
- Raspberry Pi avec Debian Bookworm "no desktop"
- Paquets requis:
```bash
sudo apt update && sudo apt install -y \
  chromium xserver-xorg xinit openbox x11-xserver-utils unclutter \
  curl nodejs npm git
```

#### 1. Cloner le projet
```bash
cd ~
git clone <URL_DU_REPO> eg-local
cd eg-local/ui/slot
npm install
```

#### 2. Configuration MQTT vers le Core
Créer `~/eg-local/ui/slot/.env`:
```bash
# Configuration MQTT pour l'application Slot UI
# Adresse du broker MQTT (IP du RPi Core)
VITE_MQTT_HOST=192.168.1.27

# Port WebSocket du broker MQTT
VITE_MQTT_PORT=9001

# Chemin WebSocket du broker MQTT
VITE_MQTT_PATH=/mqtt
```

#### 3. Script de session kiosk
Créer `~/bin/kiosk-session.sh` (exécutable):
```bash
#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0
export XDG_RUNTIME_DIR="/home/pi/.xdg"
mkdir -p "$XDG_RUNTIME_DIR"

# Wait for Xorg :0 to be ready
for i in {1..60}; do
  if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    break
  fi
  sleep 1
  printf "."
done

# Disable screensaver/power management
xset s off || true
xset -dpms || true
xset s noblank || true

# Start window manager
if ! pgrep -x openbox >/dev/null 2>&1; then
  openbox-session &
fi

# Hide mouse cursor
pgrep -x unclutter >/dev/null 2>&1 || (unclutter -idle 0 -root &)

# Wait for Vite dev server
URL="http://localhost:5173"
for i in {1..120}; do
  if curl -sSf "$URL" >/dev/null 2>&1; then
    break
  fi
  sleep 1
  printf "."
done

# Inject Core MQTT settings from .env
UI_ENV="$HOME/eg-local/ui/slot/.env"
CORE_HOST=""
if [ -f "$UI_ENV" ]; then
  CORE_HOST=$(grep -E '^VITE_MQTT_HOST=' "$UI_ENV" | sed -E 's/^VITE_MQTT_HOST=//' | tr -d '"' | xargs)
fi

if [ -n "$CORE_HOST" ]; then
  URL="${URL}/?mqtt_host=${CORE_HOST}&mqtt_port=9001&mqtt_path=/mqtt"
fi

BROWSER=chromium
exec "$BROWSER" \
  --no-first-run \
  --disable-translate \
  --kiosk \
  --incognito \
  --noerrdialogs \
  --disable-infobars \
  --app="$URL"
```

Puis: `chmod +x ~/bin/kiosk-session.sh`

#### 4. Services systemd (variante 100% systemd)
Créer les 3 services système:

**`/etc/systemd/system/eg-xorg.service`:**
```ini
[Unit]
Description=EG Xorg server on :0 for kiosk
After=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/Xorg :0 -nolisten tcp -ac -s 0 -dpms vt7
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/eg-vite.service`:**
```ini
[Unit]
Description=EG Slot UI Vite dev server
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/eg-local/ui/slot
ExecStart=/usr/bin/env bash -lc "[ -d node_modules ] || npm install; npm run dev -- --host 0.0.0.0 --port 5173 --strictPort"
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/eg-kiosk.service`:**
```ini
[Unit]
Description=EG Chromium kiosk
After=eg-xorg.service eg-vite.service
Requires=eg-xorg.service eg-vite.service

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
ExecStart=/home/pi/bin/kiosk-session.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 5. Activer les services
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now eg-xorg.service eg-vite.service eg-kiosk.service
```

#### 6. Vérifications
```bash
# État des services
sudo systemctl status eg-vite.service eg-kiosk.service

# Logs en direct
sudo journalctl -u eg-kiosk.service -f

# Test connectivité broker
curl -I http://IP_DU_CORE:9001/mqtt
```

#### 7. Personnalisation par device
Pour différencier les slots, modifier l'URL dans le script:
```bash
# Dans kiosk-session.sh:
URL="${URL}/?id=slot-02&mqtt_host=${CORE_HOST}&..."
```

Voir `agents/systemd/README-systemd.md` pour les anciens services agents.

### Configuration MQTT/API multi-RPi

Pour déployer les UIs sur des RPi différents de celui qui héberge le core/Mosquitto :

```bash
# Configuration pour chaque UI
cd ui/slot && cp .env.example .env
cd ui/change && cp .env.example .env  
cd ui/operator && cp .env.example .env

# Éditer les .env selon votre architecture
# Slot UI (.env) :
VITE_MQTT_HOST=192.168.1.100  # IP du RPi core
VITE_MQTT_PORT=9001
VITE_MQTT_PATH=/mqtt

# Change UI (.env) :
VITE_MQTT_HOST=192.168.1.100  # IP du RPi core

# Operator UI (.env) :
VITE_API_HOST=192.168.1.100   # IP du RPi core
VITE_API_PORT=8000

# Build pour production
npm run build:prod
```

**Alternatives :**
```bash
# Option 1: Build avec variables d'environnement inline
VITE_MQTT_HOST=rpi-core.local npm run build

# Option 2: Paramètres URL (runtime)
# http://rpi-ui/slot/?id=slot-01&mqtt_host=rpi-core.local
# http://rpi-ui/operator/?api_host=rpi-core.local
```

> UIs via WebSocket MQTT sur `ws://<core>:9001/mqtt`. En prod, préfère build des UIs et servir via un reverse proxy/HTTP statique (optionnel).

## Structure

- `mosquitto/` — broker MQTT (TCP 1883, WebSocket 9001, persistence ON)
- `core/` — FastAPI + SQLite (WAL), RPC wallet, payouts, night mode
- `agents/` — Python asyncio; slot agent (clavier dev par défaut)
- `ui/slot` — React UI slot (Balance/Bet/Credit + Vote)
- `ui/change` — React UI change machine (liste payouts + claim)
- `ui/operator` — mini panneau opérateur (mode/step)
- `scripts/` — scripts de test

## Notes

- QoS1 partout, `eg/state/mode` en **retained**, LWT agents `online|offline`.
- Montants en **cents** (int). Solde **jamais négatif** (UPDATE conditionnel).
- 100% local (LAN câblé). NTP actif recommandé. DHCP avec réservations MAC.
