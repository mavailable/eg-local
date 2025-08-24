#!/bin/bash

# Script de test pour le nouveau système d'entrées GPIO/Clavier/RFID

echo "=== Test du système d'entrées GPIO/Clavier/RFID ==="

# Installation des dépendances
echo "Installation des dépendances..."
cd /home/pi/eg-local/agents
pip3 install -r requirements.txt

# Démarrage du broker MQTT
echo "Démarrage du broker MQTT..."
cd /home/pi/eg-local
docker-compose up -d mosquitto

# Attendre que MQTT soit prêt
sleep 3

# Test de l'agent slot avec le nouveau système
echo "Démarrage de l'agent slot avec gestion GPIO/Clavier/RFID..."
cd /home/pi/eg-local/agents/slot
python3 slot_agent.py &
AGENT_PID=$!

# Attendre que l'agent soit prêt
sleep 5

# Démarrage de l'interface web
echo "Démarrage de l'interface web..."
cd /home/pi/eg-local/ui/slot
npm install
npm run dev &
UI_PID=$!

echo ""
echo "=== Système démarré ==="
echo "Agent PID: $AGENT_PID"
echo "UI PID: $UI_PID"
echo ""
echo "Interface web: http://localhost:5173"
echo ""
echo "Test des fonctionnalités:"
echo "1. Utilisez les touches numériques 1-6 pour allumer/éteindre les LEDs"
echo "2. Utilisez les boutons GPIO (si disponibles) pour contrôler les LEDs"
echo "3. Commandes dans l'agent:"
echo "   - 'led 0 on' : allume la LED 0"
echo "   - 'led 2 off' : éteint la LED 2"
echo "   - 'led test' : séquence de test des LEDs"
echo "   - 'r TAG123' : simule un tag RFID"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter..."

# Fonction de nettoyage
cleanup() {
    echo "Arrêt des processus..."
    kill $AGENT_PID 2>/dev/null
    kill $UI_PID 2>/dev/null
    docker-compose down
    exit 0
}

# Piège pour Ctrl+C
trap cleanup INT

# Attendre indéfiniment
wait
