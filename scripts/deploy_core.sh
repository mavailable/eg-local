#!/bin/bash

# Script de déploiement pour RPi Core (serveur central)

echo "=== Déploiement RPi Core ==="

# Configuration
CORE_HOST=${CORE_HOST:-$(hostname -I | awk '{print $1}')}
echo "Core Host: $CORE_HOST"

# Arrêt des services existants
echo "Arrêt des services existants..."
docker-compose -f docker-compose.core.yml down

# Construction et démarrage
echo "Construction et démarrage des services core..."
docker-compose -f docker-compose.core.yml up -d --build

# Vérification
echo "Vérification des services..."
sleep 5
docker-compose -f docker-compose.core.yml ps

echo ""
echo "=== Services Core démarrés ==="
echo "MQTT Broker: $CORE_HOST:1883 (TCP), $CORE_HOST:9001 (WebSocket)"
echo "API Core: http://$CORE_HOST:8000"
echo "UI Operator: http://$CORE_HOST:3000"
echo ""
echo "Configuration pour les slots:"
echo "CORE_HOST=$CORE_HOST"
