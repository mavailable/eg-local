import asyncio
import logging
from typing import Callable, Dict, Optional, List
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    # Mock GPIO pour développement
    GPIO_AVAILABLE = False
    print("Warning: RPi.GPIO not available, using mock GPIO")

class MockGPIO:
    """Mock GPIO pour développement sans Raspberry Pi"""
    BCM = "BCM"
    IN = "IN"
    OUT = "OUT"
    PUD_UP = "PUD_UP"
    LOW = 0
    HIGH = 1
    
    @staticmethod
    def setmode(mode): pass
    @staticmethod
    def setup(pin, mode, **kwargs): pass
    @staticmethod
    def input(pin): return 1  # Simule bouton non pressé
    @staticmethod
    def output(pin, value): pass
    @staticmethod
    def cleanup(): pass

class GPIOManager:
    """Gestionnaire GPIO asynchrone pour boutons et LEDs"""
    
    def __init__(self, button_pins: List[int] = None, led_pins: List[int] = None):
        self.gpio = GPIO if GPIO_AVAILABLE else MockGPIO()
        self.button_pins = button_pins or [5, 6, 22, 23, 17, 16]
        self.led_pins = led_pins or [18, 19, 20, 21, 12, 13]  # GPIO pour LEDs
        self.button_callbacks: Dict[int, Callable] = {}
        self.button_states: Dict[int, bool] = {}
        self.led_states: Dict[int, bool] = {}
        self.debounce_delay = 0.05  # 50ms anti-rebond
        self.running = False
        
        # Configuration GPIO
        self.gpio.setmode(self.gpio.BCM)
        
        # Configuration des boutons (pull-up interne, active LOW)
        for pin in self.button_pins:
            self.gpio.setup(pin, self.gpio.IN, pull_up_down=self.gpio.PUD_UP)
            self.button_states[pin] = True  # État initial (non pressé)
            
        # Configuration des LEDs
        for pin in self.led_pins:
            self.gpio.setup(pin, self.gpio.OUT)
            self.gpio.output(pin, self.gpio.LOW)
            self.led_states[pin] = False
            
        logging.info(f"GPIO Manager initialized - Buttons: {self.button_pins}, LEDs: {self.led_pins}")
    
    def set_button_callback(self, button_index: int, callback: Callable[[int], None]):
        """Définit le callback pour un bouton (index 0-5)"""
        if 0 <= button_index < len(self.button_pins):
            pin = self.button_pins[button_index]
            self.button_callbacks[pin] = callback
            logging.info(f"Callback set for button {button_index} (GPIO {pin})")
    
    def set_led_state(self, led_index: int, state: bool):
        """Allume/éteint une LED (index 0-5)"""
        if 0 <= led_index < len(self.led_pins):
            pin = self.led_pins[led_index]
            self.gpio.output(pin, self.gpio.HIGH if state else self.gpio.LOW)
            self.led_states[pin] = state
            logging.debug(f"LED {led_index} (GPIO {pin}) {'ON' if state else 'OFF'}")
    
    def toggle_led(self, led_index: int):
        """Inverse l'état d'une LED"""
        if 0 <= led_index < len(self.led_pins):
            pin = self.led_pins[led_index]
            new_state = not self.led_states[pin]
            self.set_led_state(led_index, new_state)
            return new_state
        return False
    
    def get_led_state(self, led_index: int) -> bool:
        """Retourne l'état d'une LED"""
        if 0 <= led_index < len(self.led_pins):
            pin = self.led_pins[led_index]
            return self.led_states[pin]
        return False
    
    def get_led_states(self) -> List[bool]:
        """Retourne l'état de toutes les LEDs"""
        return [self.led_states[pin] for pin in self.led_pins]
    
    async def _monitor_buttons(self):
        """Boucle de surveillance des boutons avec anti-rebond"""
        while self.running:
            for pin in self.button_pins:
                current_state = bool(self.gpio.input(pin))
                previous_state = self.button_states[pin]
                
                # Détection d'un appui (transition HIGH -> LOW)
                if previous_state and not current_state:
                    # Anti-rebond
                    await asyncio.sleep(self.debounce_delay)
                    # Vérification que le bouton est toujours pressé
                    if not bool(self.gpio.input(pin)):
                        button_index = self.button_pins.index(pin)
                        logging.info(f"Button {button_index} pressed (GPIO {pin})")
                        
                        # Appel du callback si défini
                        if pin in self.button_callbacks:
                            try:
                                self.button_callbacks[pin](button_index)
                            except Exception as e:
                                logging.error(f"Error in button callback: {e}")
                
                self.button_states[pin] = current_state
            
            await asyncio.sleep(0.01)  # Polling 100Hz
    
    async def start(self):
        """Démarre la surveillance des boutons"""
        if not self.running:
            self.running = True
            logging.info("GPIO Manager started")
            await self._monitor_buttons()
    
    def stop(self):
        """Arrête la surveillance et nettoie les GPIO"""
        self.running = False
        self.gpio.cleanup()
        logging.info("GPIO Manager stopped")
    
    async def test_sequence(self):
        """Séquence de test des LEDs"""
        logging.info("Starting LED test sequence")
        
        # Allumage séquentiel
        for i in range(len(self.led_pins)):
            self.set_led_state(i, True)
            await asyncio.sleep(0.2)
        
        await asyncio.sleep(0.5)
        
        # Extinction séquentielle
        for i in range(len(self.led_pins)):
            self.set_led_state(i, False)
            await asyncio.sleep(0.2)
        
        logging.info("LED test sequence completed")
