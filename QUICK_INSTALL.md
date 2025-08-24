# 🚀 Installation rapide EG Local

## RPi Core (serveur central)

```bash
# 1. Cloner le projet
git clone <URL_DU_REPO> ~/eg-local

# 2. Installation automatique
cd ~/eg-local
./scripts/install_core.sh

# 3. Vérification
eg-status
eg-logs
```

**Résultat :** RPi Core avec IP fixe, services auto-démarrés, monitoring SSH

---

## RPi Slot (devices)

```bash
# 1. Cloner le projet
git clone <URL_DU_REPO> ~/eg-local

# 2. Installation automatique
cd ~/eg-local
CORE_HOST=192.168.1.27 SLOT_ID=slot-01 ./scripts/install_slot.sh

# 3. Vérification
eg-status
eg-test
```

**Résultat :** RPi Slot en kiosk mode, GPIO fonctionnel, auto-démarré

---

## 🔧 Post-installation

### Core
- **Monitoring :** `ssh pi@192.168.1.27` puis `eg-logs`
- **API :** http://192.168.1.27:8000/health
- **UI Operator :** http://192.168.1.27:3000

### Slot  
- **Test GPIO :** Appuyer sur boutons physiques → LEDs s'allument
- **Test clavier :** Touches 1-6 → LEDs s'allument dans l'UI
- **Test RFID :** Approcher tag → Auto-remplissage UID
- **Logs :** `ssh pi@SLOT_IP` puis `eg-logs`

---

## 📡 Réseau type

```
Router: 192.168.1.1
├─ Core:   192.168.1.27  (fixe)
├─ Slot1:  192.168.1.31  (DHCP)
├─ Slot2:  192.168.1.32  (DHCP)
└─ Slot3:  192.168.1.33  (DHCP)
```

**Ports importants :**
- `1883` : MQTT TCP
- `9001` : MQTT WebSocket  
- `8000` : API Core
- `5173` : UI Slot locale
