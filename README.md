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

# 3) UIs (dans 3 terminaux)
cd ui/slot && npm i && npm run dev      # http://localhost:5173/?id=slot-01
cd ui/change && npm i && npm run dev    # http://localhost:5174/?id=change-01
cd ui/operator && npm i && npm run dev  # http://localhost:5175/
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

Voir `agents/systemd/README-systemd.md` (unités `eg-slot@.service` et `chromium-kiosk@.service`).

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
