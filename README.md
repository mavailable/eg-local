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

# 3) UIs (dans 2 terminaux)
cd ui/slot && npm i && npm run dev      # http://localhost:5173/?id=slot-01
cd ui/change && npm i && npm run dev    # http://localhost:5174/?id=change-01

# (Bonus) Panel opérateur
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
