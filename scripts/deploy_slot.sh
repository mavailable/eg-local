#!/bin/bash

# Script de déploiement pour RPi Slot (device)

echo "=== Déploiement RPi Slot ==="

# Configuration
CORE_HOST=${CORE_HOST:-192.168.1.27}
SLOT_ID=${SLOT_ID:-slot-01}

echo "Core Host: $CORE_HOST"
echo "Slot ID: $SLOT_ID"

# Export des variables d'environnement
export CORE_HOST
export SLOT_ID

# Arrêt des services existants
echo "Arrêt des services existants..."
docker-compose -f docker-compose.slot.yml down

# Construction et démarrage
echo "Construction et démarrage des services slot..."
docker-compose -f docker-compose.slot.yml up -d --build

# Vérification
echo "Vérification des services..."
sleep 5
docker-compose -f docker-compose.slot.yml ps

echo ""
echo "=== Services Slot démarrés ==="
echo "Slot UI: http://$(hostname -I | awk '{print $1}'):5173"
echo "Device ID: $SLOT_ID"
echo "Connecté au Core: $CORE_HOST"
echo ""
echo "Démarrage de l'agent slot..."
cd agents/slot
python3 slot_agent.py &
AGENT_PID=$!
echo "Agent PID: $AGENT_PID"

# Fonction de nettoyage
cleanup() {
    echo "Arrêt de l'agent..."
    kill $AGENT_PID 2>/dev/null
    docker-compose -f ../../docker-compose.slot.yml down
    exit 0
}

trap cleanup INT
echo "Appuyez sur Ctrl+C pour arrêter..."
wait
