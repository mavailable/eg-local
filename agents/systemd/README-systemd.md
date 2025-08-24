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
sudo cp agents/systemd/chromium-kiosk@.service /etc/systemd/system/
sudo systemctl daemon-reload
# Exemple pour slot-01 (UI Slot sur port 5173)
sudo systemctl enable --now chromium-kiosk@slot-01.service

## Logs
journalctl -u eg-slot@slot-01 -f
journalctl -u chromium-kiosk@slot-01 -f
