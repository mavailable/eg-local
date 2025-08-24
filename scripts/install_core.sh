#!/bin/bash

# Script d'installation automatique pour RPi Core
# Usage: curl -sSL https://raw.../install_core.sh | bash

set -euo pipefail

echo "=== Installation automatique RPi Core ==="
echo "Ce script va configurer ce Raspberry Pi comme serveur central EG."
echo ""

# Vérifications préliminaires
if [[ $EUID -eq 0 ]]; then
   echo "❌ Ne pas exécuter en tant que root. Utilisez l'utilisateur 'pi'."
   exit 1
fi

if ! command -v git &> /dev/null; then
    echo "📦 Installation de git..."
    sudo apt update && sudo apt install -y git
fi

# Configuration réseau
echo "🌐 Configuration réseau..."
CURRENT_IP=$(hostname -I | awk '{print $1}')
echo "IP actuelle: $CURRENT_IP"

read -p "Voulez-vous configurer une IP statique ? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "IP statique souhaitée (ex: 192.168.1.27): " STATIC_IP
    read -p "Gateway (ex: 192.168.1.1): " GATEWAY
    
    sudo tee -a /etc/dhcpcd.conf > /dev/null <<EOF

# Configuration EG Core
interface eth0
static ip_address=${STATIC_IP}/24
static routers=${GATEWAY}
static domain_name_servers=${GATEWAY}
EOF
    
    echo "✅ Configuration réseau ajoutée. Redémarrage requis après installation."
    CORE_HOST="$STATIC_IP"
else
    CORE_HOST="$CURRENT_IP"
fi

# Installation Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Installation Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker pi
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installation Docker Compose..."
    sudo apt update && sudo apt install -y docker-compose
fi

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

# Configuration
echo "⚙️  Configuration du core..."
cp .env.core .env
sed -i "s/CORE_HOST=.*/CORE_HOST=$CORE_HOST/" .env

# Service systemd
echo "🔧 Configuration du service auto-démarrage..."
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

sudo systemctl daemon-reload
sudo systemctl enable eg-core.service

# Alias utiles
echo "🛠️  Configuration des alias..."
cat >> ~/.bashrc <<EOF

# Alias EG Core
alias eg-status='sudo systemctl status eg-core.service'
alias eg-logs='docker-compose -f ~/eg-local/docker-compose.core.yml logs -f'
alias eg-restart='sudo systemctl restart eg-core.service'
alias eg-stop='sudo systemctl stop eg-core.service'
alias eg-start='sudo systemctl start eg-core.service'
EOF

# Test initial
echo "🚀 Démarrage initial..."
chmod +x ~/eg-local/scripts/deploy_core.sh
~/eg-local/scripts/deploy_core.sh

echo ""
echo "✅ Installation terminée !"
echo ""
echo "📋 Résumé de configuration:"
echo "  • IP Core: $CORE_HOST"
echo "  • MQTT: $CORE_HOST:1883 (TCP), $CORE_HOST:9001 (WebSocket)"
echo "  • API: http://$CORE_HOST:8000"
echo "  • UI Operator: http://$CORE_HOST:3000"
echo ""
echo "🔧 Commandes utiles:"
echo "  • eg-status    : État du service"
echo "  • eg-logs      : Logs en temps réel"
echo "  • eg-restart   : Redémarrer les services"
echo ""
echo "📱 Pour configurer un slot:"
echo "  export CORE_HOST=$CORE_HOST"
echo "  ./scripts/deploy_slot.sh"
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "⚠️  Redémarrage nécessaire pour appliquer la configuration réseau."
    read -p "Redémarrer maintenant ? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo reboot
    fi
fi
