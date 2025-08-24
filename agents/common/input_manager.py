import asyncio
import logging
import json
from typing import Dict, List, Optional
from .gpio_manager import GPIOManager
from .keyboard_manager import KeyboardManager
from .rfid_manager import RFIDManager, MockRFIDManager
from .mqtt_async import AsyncMqtt

class InputManager:
    """Gestionnaire centralisé des entrées (GPIO, clavier, RFID)"""
    
    def __init__(self, device_id: str, mqtt_host: str, mqtt_port: int, dev_mode: bool = True):
        self.device_id = device_id
        self.dev_mode = dev_mode
        
        # État des voyants (0-5)
        self.led_states = [False] * 6
        
        # Gestionnaires d'entrées
        self.gpio_manager = GPIOManager()
        self.keyboard_manager = KeyboardManager()
        
        # RFID : utilise le mock en mode dev ou si pas de port série
        if dev_mode:
            self.rfid_manager = MockRFIDManager()
        else:
            self.rfid_manager = RFIDManager()
        
        # MQTT
        self.mqtt = AsyncMqtt(
            client_id=f"{device_id}-input-manager",
            host=mqtt_host,
            port=mqtt_port,
            lwt_topic=f"eg/dev/{device_id}/input/status"
        )
        
        # Configuration des callbacks
        self._setup_callbacks()
        
        logging.info(f"InputManager initialized for {device_id}")
    
    def _setup_callbacks(self):
        """Configuration des callbacks pour tous les gestionnaires"""
        
        # Callbacks GPIO - boutons 0-5 toggle les LEDs correspondantes
        for i in range(6):
            self.gpio_manager.set_button_callback(i, self._on_button_press)
        
        # Callbacks clavier - touches numériques 1-6 toggle les LEDs 0-5
        self.keyboard_manager.set_number_key_callbacks(self._on_key_press)
        
        # Callback RFID
        self.rfid_manager.set_tag_callback(self._on_rfid_tag)
    
    def _on_button_press(self, button_index: int):
        """Callback pour appui de bouton GPIO"""
        logging.info(f"GPIO button {button_index} pressed")
        self._toggle_led(button_index, source="gpio")
    
    def _on_key_press(self, key_index: int):
        """Callback pour appui de touche clavier"""
        logging.info(f"Keyboard key {key_index + 1} pressed")
        self._toggle_led(key_index, source="keyboard")
    
    def _on_rfid_tag(self, tag_uid: str):
        """Callback pour détection de tag RFID"""
        logging.info(f"RFID tag detected: {tag_uid}")
        
        # Publication du tag RFID
        self._publish_mqtt(f"eg/dev/{self.device_id}/input/rfid", {
            "tag_uid": tag_uid,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    def _toggle_led(self, led_index: int, source: str = "unknown"):
        """Toggle une LED et synchronise l'état"""
        if 0 <= led_index < 6:
            # Mise à jour de l'état local
            self.led_states[led_index] = not self.led_states[led_index]
            new_state = self.led_states[led_index]
            
            # Mise à jour de la LED physique
            self.gpio_manager.set_led_state(led_index, new_state)
            
            logging.info(f"LED {led_index} toggled to {'ON' if new_state else 'OFF'} (source: {source})")
            
            # Publication de l'état des LEDs via MQTT
            self._publish_led_states()
    
    def set_led_state(self, led_index: int, state: bool):
        """Définit l'état d'une LED spécifique"""
        if 0 <= led_index < 6:
            self.led_states[led_index] = state
            self.gpio_manager.set_led_state(led_index, state)
            self._publish_led_states()
    
    def set_all_leds(self, states: List[bool]):
        """Définit l'état de toutes les LEDs"""
        if len(states) == 6:
            self.led_states = states[:]
            for i, state in enumerate(states):
                self.gpio_manager.set_led_state(i, state)
            self._publish_led_states()
    
    def _publish_led_states(self):
        """Publie l'état des LEDs via MQTT"""
        self._publish_mqtt(f"eg/dev/{self.device_id}/input/leds", {
            "states": self.led_states,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    def _publish_mqtt(self, topic: str, payload: Dict):
        """Publie un message MQTT"""
        if self.mqtt:
            self.mqtt.publish(topic, payload)
    
    async def _handle_mqtt_commands(self, topic: str, message: Dict):
        """Gestion des commandes MQTT reçues"""
        try:
            if topic == f"eg/dev/{self.device_id}/input/cmd/led":
                # Commande de contrôle des LEDs
                if "index" in message and "state" in message:
                    self.set_led_state(message["index"], message["state"])
                elif "states" in message:
                    self.set_all_leds(message["states"])
            
            elif topic == f"eg/dev/{self.device_id}/input/cmd/test":
                # Commande de test
                if message.get("action") == "led_sequence":
                    await self.gpio_manager.test_sequence()
                elif message.get("action") == "simulate_rfid":
                    tag_uid = message.get("tag_uid", "TEST1234")
                    await self.rfid_manager.simulate_tag(tag_uid)
        
        except Exception as e:
            logging.error(f"Error handling MQTT command: {e}")
    
    async def start(self):
        """Démarre tous les gestionnaires"""
        logging.info("Starting InputManager...")
        
        # Connexion MQTT
        await self.mqtt.connect()
        self.mqtt.set_status_online(f"eg/dev/{self.device_id}/input/status")
        
        # Souscription aux commandes
        self.mqtt.subscribe(f"eg/dev/{self.device_id}/input/cmd/+", self._handle_mqtt_commands)
        
        # Publication de l'état initial
        self._publish_mqtt(f"eg/dev/{self.device_id}/input/status", {
            "status": "online",
            "device_id": self.device_id,
            "led_count": 6,
            "button_count": 6,
            "capabilities": ["gpio", "keyboard", "rfid"],
            "timestamp": asyncio.get_event_loop().time()
        })
        
        self._publish_led_states()
        
        # Démarrage des gestionnaires en parallèle
        tasks = [
            asyncio.create_task(self.gpio_manager.start()),
            asyncio.create_task(self.keyboard_manager.start()),
            asyncio.create_task(self.rfid_manager.start()),
        ]
        
        # Test initial des LEDs
        if self.dev_mode:
            await asyncio.sleep(1)
            await self.gpio_manager.test_sequence()
        
        # Attendre tous les gestionnaires
        await asyncio.gather(*tasks)
    
    def stop(self):
        """Arrête tous les gestionnaires"""
        logging.info("Stopping InputManager...")
        
        self.gpio_manager.stop()
        self.keyboard_manager.stop()
        self.rfid_manager.stop()
        
        # Publication du statut offline
        self._publish_mqtt(f"eg/dev/{self.device_id}/input/status", {
            "status": "offline",
            "timestamp": asyncio.get_event_loop().time()
        })


# Configuration pour les logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
