# Système d'Entrées GPIO/Clavier/RFID

Ce système permet aux interfaces utilisateur de réagir aux entrées suivantes :
- **Boutons GPIO** : 6 boutons physiques sur les broches GPIO 5, 6, 22, 23, 17, 16
- **Touches clavier** : Touches numériques 1-6
- **Tags RFID** : Lecteur RFID série

## Architecture

### Gestionnaires d'entrées (`agents/common/`)

- **`gpio_manager.py`** : Gestion des boutons GPIO et LEDs
- **`keyboard_manager.py`** : Gestion des événements clavier
- **`rfid_manager.py`** : Gestion du lecteur RFID série
- **`input_manager.py`** : Coordination de tous les gestionnaires

### Fonctionnalités

#### 1. Boutons GPIO
- **Configuration** : 6 boutons sur GPIO 5, 6, 22, 23, 17, 16
- **Pull-up interne** : Actif (logique LOW = pressé)
- **Anti-rebond** : 50ms
- **LEDs** : 6 LEDs sur GPIO 18, 19, 20, 21, 12, 13

#### 2. Clavier
- **Touches surveillées** : 1, 2, 3, 4, 5, 6
- **Détection** : Événements evdev asynchrones
- **Fonctionnalité** : Chaque touche toggle la LED correspondante

#### 3. RFID
- **Interface** : Série (USB/UART)
- **Format** : Tags hexadécimaux
- **Auto-remplissage** : Le tag détecté remplit automatiquement le champ UID

## Configuration

### Installation des dépendances

```bash
cd agents
pip3 install -r requirements.txt
```

### Configuration matérielle

#### GPIO (Raspberry Pi)
```python
# Boutons (pull-up interne)
BUTTON_PINS = [5, 6, 22, 23, 17, 16]

# LEDs 
LED_PINS = [18, 19, 20, 21, 12, 13]
```

#### RFID
- Port série : `/dev/ttyUSB0` (par défaut)
- Baud rate : 9600
- Format : Tags hexadécimaux terminés par CR/LF

## Utilisation

### Démarrage du système

1. **Agent slot avec entrées**
```bash
cd agents/slot
python3 slot_agent.py
```

2. **Interface web**
```bash
cd ui/slot
npm run dev
```

### Contrôle des LEDs

#### Via clavier/GPIO
- Touche **1** ou bouton **GPIO 5** → Toggle LED 0
- Touche **2** ou bouton **GPIO 6** → Toggle LED 1
- ... et ainsi de suite

#### Via interface web
- Clic sur une LED pour la toggle
- Bouton "Test LED Sequence" pour tester toutes les LEDs

#### Via commandes texte (agent)
```bash
led 0 on      # Allume LED 0
led 2 off     # Éteint LED 2
led test      # Séquence de test
```

#### Via MQTT
```json
// Toggle LED 3
Topic: eg/dev/slot-01/input/cmd/led
Payload: {"index": 3, "state": true}

// Test des LEDs
Topic: eg/dev/slot-01/input/cmd/test
Payload: {"action": "led_sequence"}
```

### Événements MQTT

#### État des LEDs
```json
Topic: eg/dev/slot-01/input/leds
Payload: {
  "states": [true, false, true, false, false, true],
  "timestamp": 1234567890.123
}
```

#### Tag RFID détecté
```json
Topic: eg/dev/slot-01/input/rfid
Payload: {
  "tag_uid": "04A37C91",
  "timestamp": 1234567890.123
}
```

#### Statut du gestionnaire
```json
Topic: eg/dev/slot-01/input/status
Payload: {
  "status": "online",
  "device_id": "slot-01",
  "led_count": 6,
  "button_count": 6,
  "capabilities": ["gpio", "keyboard", "rfid"],
  "timestamp": 1234567890.123
}
```

## Tests

### Script de test automatique
```bash
./scripts/test_input_system.sh
```

### Tests manuels

#### 1. Test des LEDs
- Appuyez sur les touches 1-6
- Vérifiez que les LEDs correspondantes s'allument/s'éteignent
- Vérifiez la synchronisation avec l'interface web

#### 2. Test RFID
- Approchez un tag RFID du lecteur
- Vérifiez que le champ UID se remplit automatiquement
- Vérifiez l'affichage dans les logs de l'agent

#### 3. Test GPIO
- Appuyez sur les boutons physiques
- Vérifiez le toggle des LEDs correspondantes

## Mode développement

En mode dev (`dev_mode: true`), le système utilise des mocks :
- **GPIO Mock** : Simule les GPIO sans Raspberry Pi
- **RFID Mock** : Génère des tags test automatiquement
- **Clavier** : Fonctionne normalement si evdev est disponible

## Dépannage

### GPIO non disponible
```
Warning: RPi.GPIO not available, using mock GPIO
```
→ Normal en développement, installer RPi.GPIO sur Raspberry Pi

### evdev non disponible
```
Warning: evdev not available, keyboard input disabled
```
→ `pip3 install evdev` (Linux uniquement)

### RFID non connecté
```
Could not connect to RFID reader: [Errno 2] No such file or directory: '/dev/ttyUSB0'
```
→ Vérifier la connexion USB du lecteur RFID

### Permissions GPIO
```
RuntimeError: No access to /dev/mem
```
→ Exécuter avec `sudo` ou ajouter l'utilisateur au groupe `gpio`

## Extension

### Ajouter de nouveaux types d'entrées

1. Créer un nouveau gestionnaire dans `agents/common/`
2. L'intégrer dans `input_manager.py`
3. Ajouter les topics MQTT correspondants
4. Mettre à jour l'interface web pour afficher les nouveaux événements
