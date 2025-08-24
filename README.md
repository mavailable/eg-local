# EG Local — Casino / Escape Game (GPIO + RFID + MQTT)

**Version:** 2.0 — 24 août 2025  
**Nouvelles fonctionnalités :** GPIO, Clavier, RFID, Architecture distribuée

## 🎯 Vue d'ensemble

Système distribué pour casino/escape game avec :
- **RPi Core** : Broker MQTT + API + Base de données (serveur central)
- **RPi Slots** : Interfaces slot avec GPIO, clavier, RFID (devices autonomes)
- **Communication** : MQTT temps réel entre tous les composants

### 🔧 Fonctionnalités

#### 🎰 **Device Slot**
- **6 boutons GPIO** (broches 5,6,22,23,17,16) avec anti-rebond
- **6 LEDs de statut** (broches 18,19,20,21,12,13) 
- **Clavier** : touches 1-6 pour contrôler les LEDs
- **Lecteur RFID série** avec auto-remplissage
- **Interface web** moderne avec voyants interactifs
- **Mode kiosk** : démarrage automatique au boot

#### 🏗️ **Core centralisé**
- **Broker MQTT** (Mosquitto) : TCP 1883 + WebSocket 9001
- **API REST** : Gestion wallet, payouts, mode nuit
- **Base SQLite** : Persistance des données
- **Interface opérateur** : Contrôle global du système

---

## 🚀 Démarrage rapide

### **Option 1: Développement local**
```bash
# 1) Infrastructure (broker MQTT + API)
docker compose up -d

# 2) Agent slot avec GPIO/clavier/RFID
cd agents/slot
pip3 install -r ../requirements.txt
python3 slot_agent.py

# 3) Interface web slot
cd ui/slot && npm i && npm run dev
# http://localhost:5173/?id=slot-01

# Test: Appuyez sur les touches 1-6 pour allumer/éteindre les LEDs
```

### **Option 2: Architecture distribuée (production)**
```bash
# Sur RPi Core (serveur central)
./scripts/deploy_core.sh

# Sur RPi Slot (devices)
export CORE_HOST=192.168.1.27  # IP du core
./scripts/deploy_slot.sh
```

---

## 🏗️ Installation RPi Core (serveur central)

### **Prérequis**
- Raspberry Pi 4 (4GB+ recommandé)
- Raspberry Pi OS Lite (64-bit)
- Docker + Docker Compose
- Connexion réseau fixe (Ethernet recommandé)

### **1. Préparation système**
```bash
# Mise à jour système
sudo apt update && sudo apt upgrade -y

# Installation Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pi

# Installation Docker Compose
sudo apt install -y docker-compose

# Redémarrer pour appliquer les groupes
sudo reboot
```

### **2. Installation du projet**
```bash
# Cloner le projet
cd ~
git clone <URL_DU_REPO> eg-local
cd eg-local

# Configuration réseau
sudo nano /etc/dhcpcd.conf
# Ajouter (adapter selon votre réseau) :
# interface eth0
# static ip_address=192.168.1.27/24
# static routers=192.168.1.1
# static domain_name_servers=192.168.1.1
```

### **3. Configuration du core**
```bash
# Copier la configuration
cp .env.core .env

# Éditer si nécessaire
nano .env
# CORE_HOST=192.168.1.27
# MQTT_PORT=1883
# MQTT_WS_PORT=9001
```

### **4. Service de démarrage automatique**
```bash
# Service systemd pour auto-démarrage
sudo tee /etc/systemd/system/eg-core.service > /dev/null <<EOF
[Unit]
Description=EG Core Services (MQTT + API + UI)
After=network-online.target docker.service
Requires=docker.service
StartLimitIntervalSec=0

[Service]
Type=oneshot
RemainAfterExit=yes
User=pi
WorkingDirectory=/home/pi/eg-local
ExecStart=/usr/bin/docker-compose -f docker-compose.core.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.core.yml down
TimeoutStartSec=300
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Activer le service
sudo systemctl daemon-reload
sudo systemctl enable eg-core.service
```

### **5. Démarrage et vérification**
```bash
# Démarrage initial
./scripts/deploy_core.sh

# Vérification des services
docker ps
sudo systemctl status eg-core.service

# Test des endpoints
curl http://localhost:8000/health
curl http://localhost:1883  # Doit répondre (connexion fermée = normal)

# Logs
docker-compose -f docker-compose.core.yml logs -f
```

### **6. Monitoring SSH permanent**
```bash
# Configuration SSH pour monitoring
sudo systemctl enable ssh

# Optionnel: écran pour monitoring continu
sudo apt install -y screen
echo 'alias monitor="screen -S monitor docker-compose -f ~/eg-local/docker-compose.core.yml logs -f"' >> ~/.bashrc

# Utilisation: ssh pi@192.168.1.27, puis : monitor
```

---

## 🎰 Installation RPi Slot (devices)

### **Prérequis matériel**
- Raspberry Pi 4 (2GB minimum)
- **6 boutons** connectés aux GPIO 5,6,22,23,17,16 (pull-up interne)
- **6 LEDs** connectées aux GPIO 18,19,20,21,12,13 (avec résistances)
- **Lecteur RFID USB** (optionnel) : `/dev/ttyUSB0`
- Écran pour interface kiosk
- Clavier USB (pour tests)

### **Schéma de câblage GPIO**
```
Boutons (Active LOW, pull-up interne) :
├─ Bouton 1 → GPIO 5  ──┐
├─ Bouton 2 → GPIO 6  ──┤
├─ Bouton 3 → GPIO 22 ──┤ → GND commun
├─ Bouton 4 → GPIO 23 ──┤
├─ Bouton 5 → GPIO 17 ──┤
└─ Bouton 6 → GPIO 16 ──┘

LEDs (+ résistances 220Ω) :
├─ LED 1 → GPIO 18 → 220Ω → 3.3V
├─ LED 2 → GPIO 19 → 220Ω → 3.3V  
├─ LED 3 → GPIO 20 → 220Ω → 3.3V
├─ LED 4 → GPIO 21 → 220Ω → 3.3V
├─ LED 5 → GPIO 12 → 220Ω → 3.3V
└─ LED 6 → GPIO 13 → 220Ω → 3.3V
```

### **1. Préparation système**
```bash
# Système minimal (pas de bureau)
sudo apt update && sudo apt upgrade -y

# Paquets pour kiosk + GPIO
sudo apt install -y \
  chromium xserver-xorg xinit openbox x11-xserver-utils unclutter \
  curl nodejs npm git python3-pip python3-dev

# Permissions GPIO
sudo usermod -a -G gpio pi
```

### **2. Installation du projet**
```bash
# Cloner le projet
cd ~
git clone <URL_DU_REPO> eg-local
cd eg-local

# Installation dépendances Python
cd agents
pip3 install -r requirements.txt

# Installation dépendances Node.js
cd ../ui/slot
npm install
```

### **3. Configuration du slot**
```bash
# Configuration environnement
cp /home/pi/eg-local/.env.slot .env
nano .env

# Exemple configuration :
# CORE_HOST=192.168.1.27    # IP du RPi core
# SLOT_ID=slot-01           # ID unique du slot
# DEV_MODE=false            # Mode production
# RFID_PORT=/dev/ttyUSB0    # Port RFID (si connecté)
```

### **4. Script kiosk optimisé**
```bash
# Créer le script de session kiosk
mkdir -p ~/bin
tee ~/bin/kiosk-session.sh > /dev/null <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0
export XDG_RUNTIME_DIR="/home/pi/.xdg"
mkdir -p "$XDG_RUNTIME_DIR"

# Attendre Xorg
for i in {1..60}; do
  if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then break; fi
  sleep 1
done

# Configuration écran
xset s off -dpms s noblank || true

# Gestionnaire de fenêtres
pgrep -x openbox >/dev/null || openbox-session &

# Masquer le curseur
pgrep -x unclutter >/dev/null || unclutter -idle 0 -root &

# Charger la configuration
source /home/pi/eg-local/.env.slot 2>/dev/null || true
CORE_HOST=${CORE_HOST:-192.168.1.27}
SLOT_ID=${SLOT_ID:-slot-01}

# Attendre l'UI
URL="http://localhost:5173"
for i in {1..120}; do
  if curl -sSf "$URL" >/dev/null 2>&1; then break; fi
  sleep 1
done

# URL avec paramètres
URL="${URL}/?id=${SLOT_ID}&mqtt_host=${CORE_HOST}&mqtt_port=9001&mqtt_path=/mqtt"

# Lancer Chromium en kiosk
exec chromium \
  --no-first-run --disable-translate --kiosk --incognito \
  --noerrdialogs --disable-infobars --app="$URL"
EOF

chmod +x ~/bin/kiosk-session.sh
```

### **5. Services systemd pour auto-démarrage**
```bash
# Service Xorg
sudo tee /etc/systemd/system/eg-xorg.service > /dev/null <<EOF
[Unit]
Description=EG Xorg server for kiosk
After=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/Xorg :0 -nolisten tcp -ac -s 0 -dpms vt7
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Service Interface Web
sudo tee /etc/systemd/system/eg-slot-ui.service > /dev/null <<EOF
[Unit]
Description=EG Slot UI (Vite)
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/eg-local/ui/slot
Environment=NODE_ENV=production
ExecStartPre=/bin/bash -c 'cd /home/pi/eg-local/ui/slot && [ -d node_modules ] || npm install'
ExecStart=/usr/bin/npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Service Agent Slot (GPIO/RFID)
sudo tee /etc/systemd/system/eg-slot-agent.service > /dev/null <<EOF
[Unit]
Description=EG Slot Agent (GPIO/Keyboard/RFID)
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/eg-local/agents/slot
Environment=PYTHONPATH=/home/pi/eg-local/agents
ExecStartPre=/bin/bash -c 'source /home/pi/eg-local/.env.slot'
ExecStart=/usr/bin/python3 slot_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Service Kiosk
sudo tee /etc/systemd/system/eg-slot-kiosk.service > /dev/null <<EOF
[Unit]
Description=EG Slot Kiosk (Chromium)
After=eg-xorg.service eg-slot-ui.service
Requires=eg-xorg.service eg-slot-ui.service

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
ExecStart=/home/pi/bin/kiosk-session.sh
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF
```

### **6. Activation des services**
```bash
# Activer tous les services
sudo systemctl daemon-reload
sudo systemctl enable --now \
  eg-xorg.service \
  eg-slot-ui.service \
  eg-slot-agent.service \
  eg-slot-kiosk.service

# Redémarrer pour test complet
sudo reboot
```

### **7. Vérification et tests**
```bash
# État des services
sudo systemctl status eg-slot-*

# Logs en temps réel
sudo journalctl -u eg-slot-agent.service -f

# Test GPIO (si en SSH)
cd ~/eg-local/agents
python3 demo_input_system.py

# Test connexion MQTT vers core
./test_mqtt_connection.py 192.168.1.27
```

---

## 🔧 Tests et vérification

### **Test du système complet**
```bash
# 1. Test de connexion MQTT
./agents/test_mqtt_connection.py 192.168.1.27

# 2. Test des LEDs via interface web
# → Ouvrir http://SLOT_IP:5173
# → Cliquer sur les LEDs ou appuyer sur touches 1-6

# 3. Test GPIO physique (si câblé)
# → Appuyer sur les boutons physiques
# → Vérifier que les LEDs correspondantes s'allument

# 4. Test RFID (si connecté)
# → Approcher un tag RFID
# → Vérifier auto-remplissage du champ UID
```

### **Endpoints de test**
```bash
# API Core
curl http://192.168.1.27:8000/health
curl http://192.168.1.27:8000/api/payouts

# MQTT Topics (via mosquitto_sub)
mosquitto_sub -h 192.168.1.27 -t "eg/dev/+/input/leds"
mosquitto_sub -h 192.168.1.27 -t "eg/dev/+/input/rfid"
```

---

## 📁 Structure du projet

```
├── core/                   # API FastAPI + DB
├── mosquitto/              # Config broker MQTT
├── agents/                 # Agents Python
│   ├── common/            # Modules partagés
│   │   ├── gpio_manager.py      # Gestion GPIO + LEDs
│   │   ├── keyboard_manager.py  # Gestion clavier
│   │   ├── rfid_manager.py      # Gestion RFID
│   │   └── input_manager.py     # Coordinateur
│   └── slot/              # Agent slot
│       └── slot_agent.py        # Agent principal
├── ui/                    # Interfaces React
│   ├── slot/              # Interface slot
│   ├── operator/          # Interface opérateur  
│   └── change/            # Interface changeur
├── scripts/               # Scripts utilitaires
│   ├── deploy_core.sh           # Déploiement core
│   ├── deploy_slot.sh           # Déploiement slot
│   └── test_input_system.sh     # Tests complets
├── docker-compose.core.yml      # Services core
├── docker-compose.slot.yml      # Services slot
└── DISTRIBUTED_SETUP.md         # Guide détaillé
```

---

## 🌐 Architecture réseau

```
┌─────────────────────┐
│     RPi Core        │ 192.168.1.27
│                     │
│  ┌───────────────┐  │ :1883 (MQTT TCP)
│  │   Mosquitto   │◄─┼─:9001 (MQTT WebSocket)
│  └───────────────┘  │ :8000 (API REST)
│  ┌───────────────┐  │ :3000 (UI Operator)
│  │   Core API    │  │
│  └───────────────┘  │
└─────────────────────┘
          │
          │ MQTT
    ┌─────┼─────┐
    │           │
┌───▼──────┐ ┌──▼──────┐
│RPi Slot1 │ │RPi Slot2│ 192.168.1.31, 32...
│          │ │         │
│ :5173 UI │ │ :5173 UI│ (Kiosk mode)
│ GPIO+LED │ │ GPIO+LED│ (Boutons/LEDs)
│ RFID     │ │ RFID    │ (Lecteurs)
└──────────┘ └─────────┘
```

---

## 🔧 Dépannage

### **"Input Status: disconnected"**
```bash
# 1. Vérifier l'agent slot
sudo systemctl status eg-slot-agent.service
sudo journalctl -u eg-slot-agent.service -f

# 2. Vérifier la connexion MQTT
./agents/test_mqtt_connection.py $CORE_HOST

# 3. Redémarrer l'agent
sudo systemctl restart eg-slot-agent.service
```

### **Interface kiosk ne s'affiche pas**
```bash
# Vérifier Xorg
sudo systemctl status eg-xorg.service

# Vérifier l'UI
sudo systemctl status eg-slot-ui.service
curl http://localhost:5173

# Vérifier le kiosk
sudo journalctl -u eg-slot-kiosk.service -f
```

### **GPIO non fonctionnel**
```bash
# Vérifier les permissions
groups pi  # Doit contenir 'gpio'

# Test GPIO manuel
cd ~/eg-local/agents
python3 -c "
from common.gpio_manager import GPIOManager
gm = GPIOManager()
gm.set_led_state(0, True)  # Allumer LED 1
"
```

---

## 📚 Documentation complète

- **[DISTRIBUTED_SETUP.md](DISTRIBUTED_SETUP.md)** - Guide architecture distribuée
- **[INPUT_SYSTEM.md](INPUT_SYSTEM.md)** - Documentation GPIO/Clavier/RFID
- **[agents/requirements.txt](agents/requirements.txt)** - Dépendances Python

---

## 🎯 Notes importantes

- **Montants** : toujours en centimes (int)
- **GPIO** : Pull-up interne, logique active LOW
- **MQTT** : QoS 1, topics retained pour l'état
- **Réseau** : LAN filaire recommandé, DHCP avec réservations MAC
- **Sécurité** : Système local uniquement (pas d'exposition Internet)
