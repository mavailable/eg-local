# Architecture distribuée pour le projet EG

## Setup actuel
- **Core (RPi central)** : Broker MQTT + API + Base de données
- **Slots (RPi devices)** : Agents + UI locales connectées au core via MQTT

## Configuration recommandée

### 📡 **RPi Core (serveur central)**
```yaml
# docker-compose.core.yml
version: "3.9"
services:
  mosquitto:
    image: eclipse-mosquitto:2
    container_name: eg-mosquitto
    restart: unless-stopped
    ports:
      - "1883:1883"    # MQTT
      - "9001:9001"    # WebSocket MQTT
    volumes:
      - ./mosquitto/conf:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
    networks:
      - eg-network

  core:
    build: ./core
    container_name: eg-core
    restart: unless-stopped
    environment:
      - MQTT_HOST=mosquitto
      - MQTT_PORT=1883
      - CORE_DEVICE_ID=core-01
      - DB_PATH=/data/eg.db
      - NIGHT_EXPECTED_VOTES=9
    depends_on:
      - mosquitto
    ports:
      - "8000:8000"    # API Core
    volumes:
      - core-data:/data
    networks:
      - eg-network

  # Interface web centralisée (optionnel)
  operator-ui:
    build: 
      context: ./ui/operator
      dockerfile: Dockerfile
    container_name: eg-operator-ui
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - VITE_MQTT_HOST=localhost
      - VITE_MQTT_PORT=9001
    networks:
      - eg-network

volumes:
  core-data:

networks:
  eg-network:
    driver: bridge
```

### 🎰 **RPi Slot (devices)**
```yaml
# docker-compose.slot.yml
version: "3.9"
services:
  slot-ui:
    build: 
      context: ./ui/slot
      dockerfile: Dockerfile
    container_name: eg-slot-ui-${SLOT_ID:-01}
    restart: unless-stopped
    ports:
      - "5173:5173"
    environment:
      - VITE_MQTT_HOST=${CORE_HOST:-192.168.1.27}
      - VITE_MQTT_PORT=9001
      - VITE_DEVICE_ID=${SLOT_ID:-slot-01}
    networks:
      - slot-network

networks:
  slot-network:
    driver: bridge
```

## Guide de déploiement

### 🏗️ **Setup RPi Core (serveur central)**

1. **Sur le Raspberry Pi core** :
```bash
cd /path/to/eg-local

# Configuration
cp .env.core .env
source .env

# Déploiement
./scripts/deploy_core.sh
```

2. **Vérification** :
```bash
# Services Docker
docker ps

# Logs
docker-compose -f docker-compose.core.yml logs -f

# Test MQTT local
mosquitto_pub -h localhost -t "test" -m "hello"
```

### 🎰 **Setup RPi Slot (devices)**

1. **Configuration du device** :
```bash
cd /path/to/eg-local

# Configuration pour ce slot
export CORE_HOST=192.168.1.27  # IP du RPi core
export SLOT_ID=slot-02         # ID unique du slot

# Optionnel: créer un .env.slot local
echo "CORE_HOST=$CORE_HOST" > .env.slot
echo "SLOT_ID=$SLOT_ID" >> .env.slot
```

2. **Test de connexion** :
```bash
# Test MQTT vers le core
./agents/test_mqtt_connection.py $CORE_HOST

# Doit afficher "✓ Connexion réussie !"
```

3. **Installation des dépendances** :
```bash
cd agents
pip3 install -r requirements.txt
```

4. **Déploiement** :
```bash
# Démarrage complet (UI + Agent)
./scripts/deploy_slot.sh

# OU démarrage manuel
docker-compose -f docker-compose.slot.yml up -d
cd agents/slot && python3 slot_agent.py
```

### 🔧 **Résolution de problèmes**

#### Input Status "disconnected"
```bash
# 1. Vérifier la connexion MQTT
./agents/test_mqtt_connection.py

# 2. Vérifier l'agent slot
ps aux | grep slot_agent

# 3. Redémarrer l'agent avec logs
cd agents/slot
python3 slot_agent.py

# L'UI devrait montrer "Input Status: online" quand l'agent démarre
```

#### Broker MQTT inaccessible
```bash
# Sur le core, vérifier mosquitto
docker logs eg-mosquitto

# Vérifier les ports
ss -tuln | grep 1883
ss -tuln | grep 9001

# Tester depuis le slot
telnet $CORE_HOST 1883
```

### 📡 **Architecture réseau**

```
┌─────────────────┐     MQTT     ┌─────────────────┐
│   RPi Core      │◄─────────────┤   RPi Slot 1    │
│                 │              │                 │
│ ┌─────────────┐ │              │ ┌─────────────┐ │
│ │ Mosquitto   │ │              │ │ Slot Agent  │ │
│ │ :1883/9001  │ │              │ │ + GPIO      │ │
│ └─────────────┘ │              │ └─────────────┘ │
│ ┌─────────────┐ │              │ ┌─────────────┐ │
│ │ Core API    │ │              │ │ Slot UI     │ │
│ │ :8000       │ │              │ │ :5173       │ │
│ └─────────────┘ │              │ └─────────────┘ │
│ ┌─────────────┐ │              └─────────────────┘
│ │ Operator UI │ │                       │
│ │ :3000       │ │     MQTT              │
│ └─────────────┘ │◄──────────────────────┤
└─────────────────┘                       │
         │                                │
         │                                │
         └────────────────────────────────┤
                                          │
                           ┌─────────────────┐
                           │   RPi Slot 2    │
                           │                 │
                           │ ┌─────────────┐ │
                           │ │ Slot Agent  │ │
                           │ │ + GPIO      │ │
                           │ └─────────────┘ │
                           │ ┌─────────────┐ │
                           │ │ Slot UI     │ │
                           │ │ :5173       │ │
                           │ └─────────────┘ │
                           └─────────────────┘
```

### 🔑 **Variables importantes**

- **CORE_HOST** : IP du RPi core (ex: 192.168.1.27)
- **SLOT_ID** : ID unique du slot (ex: slot-01, slot-02...)
- **MQTT ports** : 1883 (TCP), 9001 (WebSocket)
