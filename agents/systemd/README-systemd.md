# Déploiement systemd sur RPi

## Copier les sources
sudo mkdir -p /opt/eg/agents/slot/configs
sudo rsync -av ./agents/ /opt/eg/agents/

## Configurer 9 slots
for n in 01 02 03 04 05 06 07 08 09; do
  sudo cp /opt/eg/agents/slot/device_config.yaml /opt/eg/agents/slot/configs/slot-$n.yaml
  sudo sed -i "s/slot-01/slot-$n/" /opt/eg/agents/slot/configs/slot-$n.yaml
done

## Installer l’unité slot
sudo cp agents/systemd/eg-slot@.service /etc/systemd/system/
sudo systemctl daemon-reload

for n in 01 02 03 04 05 06 07 08 09; do
  sudo systemctl enable --now eg-slot@slot-$n.service
done

## Kiosk Chromium (UI)

### 1. Configuration des UIs pour multi-RPi
```bash
# Si ce RPi n'héberge pas le core, configurer l'adresse du core
sudo mkdir -p /opt/eg/ui-configs

# Configuration pour UIs MQTT (slot, change)
cat > /opt/eg/ui-configs/.env.slot << EOF
VITE_MQTT_HOST=192.168.1.100
VITE_MQTT_PORT=9001
VITE_MQTT_PATH=/mqtt
EOF

cat > /opt/eg/ui-configs/.env.change << EOF
VITE_MQTT_HOST=192.168.1.100
VITE_MQTT_PORT=9001
VITE_MQTT_PATH=/mqtt
EOF

# Configuration pour UI opérateur (API HTTP)
cat > /opt/eg/ui-configs/.env.operator << EOF
VITE_API_HOST=192.168.1.100
VITE_API_PORT=8000
EOF
```

### 2. Installation du service kiosk
```bash
sudo cp agents/systemd/chromium-kiosk@.service /etc/systemd/system/
sudo systemctl daemon-reload

# Exemples d'URLs avec configuration
# Slot UI avec config MQTT
chromium --kiosk "http://localhost:5173/?id=slot-01&mqtt_host=192.168.1.100"

# Operator UI avec config API  
chromium --kiosk "http://localhost:5175/?api_host=192.168.1.100"

# Activation des services
sudo systemctl enable --now chromium-kiosk@slot-01.service
```

## Logs
journalctl -u eg-slot@slot-01 -f
journalctl -u chromium-kiosk@slot-01 -f
