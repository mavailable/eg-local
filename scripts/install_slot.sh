#!/bin/bash

# Script d'installation automatique pour RPi Slot
# Usage: curl -sSL https://raw.../install_slot.sh | bash
# ou: CORE_HOST=192.168.1.27 SLOT_ID=slot-02 ./install_slot.sh

set -euo pipefail

echo "=== Installation automatique RPi Slot ==="
echo "Ce script va configurer ce Raspberry Pi comme device slot EG."
echo ""

# Configuration
CORE_HOST=${CORE_HOST:-}
SLOT_ID=${SLOT_ID:-}

if [ -z "$CORE_HOST" ]; then
    read -p "IP du RPi Core (ex: 192.168.1.27): " CORE_HOST
fi

if [ -z "$SLOT_ID" ]; then
    read -p "ID du slot (ex: slot-01): " SLOT_ID
fi

echo "Configuration:"
echo "  • Core: $CORE_HOST"
echo "  • Slot ID: $SLOT_ID"
echo ""

# Vérifications
if [[ $EUID -eq 0 ]]; then
   echo "❌ Ne pas exécuter en tant que root. Utilisez l'utilisateur 'pi'."
   exit 1
fi

# Test de connexion au core
echo "🔍 Test de connexion au core..."
if ! ping -c 1 "$CORE_HOST" &> /dev/null; then
    echo "❌ Impossible de joindre le core à $CORE_HOST"
    echo "Vérifiez la connectivité réseau et l'IP du core."
    exit 1
fi

# Installation des paquets système
echo "📦 Installation des dépendances système..."
sudo apt update && sudo apt install -y \
  chromium xserver-xorg xinit openbox x11-xserver-utils unclutter \
  curl nodejs npm git python3-pip python3-dev

# Permissions GPIO
echo "🔧 Configuration des permissions GPIO..."
sudo usermod -a -G gpio pi

# Clone du projet
echo "📁 Récupération du projet..."
cd ~
if [ -d "eg-local" ]; then
    echo "⚠️  Dossier eg-local existe déjà. Sauvegarde..."
    mv eg-local "eg-local.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Note: Remplacer par l'URL réelle du repo
echo "⚠️  Veuillez cloner manuellement le repository:"
echo "git clone <URL_DU_REPO> ~/eg-local"
echo "Puis relancer ce script."

if [ ! -d "~/eg-local" ]; then
    echo "❌ Projet non trouvé. Clonez d'abord le repository."
    exit 1
fi

cd ~/eg-local

# Installation dépendances Python
echo "🐍 Installation des dépendances Python..."
cd agents
pip3 install -r requirements.txt

# Installation dépendances Node.js
echo "📦 Installation des dépendances Node.js..."
cd ../ui/slot
npm install

# Configuration
echo "⚙️  Configuration du slot..."
cd ~/eg-local
cp .env.slot .env
sed -i "s/CORE_HOST=.*/CORE_HOST=$CORE_HOST/" .env
sed -i "s/SLOT_ID=.*/SLOT_ID=$SLOT_ID/" .env

# Script kiosk
echo "🖥️  Configuration du mode kiosk..."
mkdir -p ~/bin
tee ~/bin/kiosk-session.sh > /dev/null <<EOF
#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0
export XDG_RUNTIME_DIR="/home/pi/.xdg"
mkdir -p "\$XDG_RUNTIME_DIR"

# Attendre Xorg
for i in {1..60}; do
  if xdpyinfo -display "\$DISPLAY" >/dev/null 2>&1; then break; fi
  sleep 1
done

# Configuration écran
xset s off -dpms s noblank || true

# Gestionnaire de fenêtres
pgrep -x openbox >/dev/null || openbox-session &

# Masquer le curseur
pgrep -x unclutter >/dev/null || unclutter -idle 0 -root &

# Charger la configuration
source /home/pi/eg-local/.env 2>/dev/null || true
CORE_HOST=\${CORE_HOST:-$CORE_HOST}
SLOT_ID=\${SLOT_ID:-$SLOT_ID}

# Attendre l'UI
URL="http://localhost:5173"
for i in {1..120}; do
  if curl -sSf "\$URL" >/dev/null 2>&1; then break; fi
  sleep 1
done

# URL avec paramètres
URL="\${URL}/?id=\${SLOT_ID}&mqtt_host=\${CORE_HOST}&mqtt_port=9001&mqtt_path=/mqtt"

# Lancer Chromium en kiosk
exec chromium \\
  --no-first-run --disable-translate --kiosk --incognito \\
  --noerrdialogs --disable-infobars --app="\$URL"
EOF

chmod +x ~/bin/kiosk-session.sh

# Services systemd
echo "🔧 Configuration des services systemd..."

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

# Service Agent Slot
sudo tee /etc/systemd/system/eg-slot-agent.service > /dev/null <<EOF
[Unit]
Description=EG Slot Agent (GPIO/Keyboard/RFID)
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/eg-local/agents/slot
Environment=PYTHONPATH=/home/pi/eg-local/agents
EnvironmentFile=/home/pi/eg-local/.env
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

# Activation des services
echo "🚀 Activation des services..."
sudo systemctl daemon-reload
sudo systemctl enable --now \
  eg-xorg.service \
  eg-slot-ui.service \
  eg-slot-agent.service \
  eg-slot-kiosk.service

# Alias utiles
echo "🛠️  Configuration des alias..."
cat >> ~/.bashrc <<EOF

# Alias EG Slot
alias eg-status='sudo systemctl status eg-slot-*'
alias eg-logs='sudo journalctl -u eg-slot-agent.service -f'
alias eg-ui-logs='sudo journalctl -u eg-slot-ui.service -f'
alias eg-kiosk-logs='sudo journalctl -u eg-slot-kiosk.service -f'
alias eg-restart='sudo systemctl restart eg-slot-*'
alias eg-stop='sudo systemctl stop eg-slot-*'
alias eg-start='sudo systemctl start eg-slot-*'
alias eg-test='cd ~/eg-local/agents && python3 test_mqtt_connection.py $CORE_HOST'
EOF

# Test de connexion
echo "🔍 Test de connexion MQTT..."
cd ~/eg-local/agents
if python3 test_mqtt_connection.py "$CORE_HOST"; then
    echo "✅ Connexion MQTT réussie !"
else
    echo "⚠️  Problème de connexion MQTT. Vérifiez que le core est démarré."
fi

echo ""
echo "✅ Installation terminée !"
echo ""
echo "📋 Résumé de configuration:"
echo "  • Slot ID: $SLOT_ID"
echo "  • Core: $CORE_HOST"
echo "  • UI locale: http://$(hostname -I | awk '{print $1}'):5173"
echo ""
echo "🔧 Commandes utiles:"
echo "  • eg-status      : État des services"
echo "  • eg-logs        : Logs agent en temps réel"
echo "  • eg-ui-logs     : Logs interface web"
echo "  • eg-kiosk-logs  : Logs kiosk"
echo "  • eg-test        : Test connexion MQTT"
echo "  • eg-restart     : Redémarrer tous les services"
echo ""
echo "💡 Le système démarre automatiquement au boot."
echo "   L'écran affichera l'interface slot en mode kiosk."
echo ""

read -p "Redémarrer maintenant pour activer le mode kiosk ? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo reboot
fi
