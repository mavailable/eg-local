import asyncio
import logging
from typing import Callable, Optional, Dict
try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    print("Warning: evdev not available, keyboard input disabled")

class KeyboardManager:
    """Gestionnaire d'entrées clavier asynchrone"""
    
    def __init__(self):
        self.devices = []
        self.key_callbacks: Dict[int, Callable] = {}
        self.running = False
        
        if EVDEV_AVAILABLE:
            # Recherche des périphériques clavier
            try:
                devices = [InputDevice(path) for path in evdev.list_devices()]
                self.devices = [dev for dev in devices if 'kbd' in dev.name.lower() or 'keyboard' in dev.name.lower()]
                logging.info(f"Found {len(self.devices)} keyboard devices")
                for dev in self.devices:
                    logging.info(f"  - {dev.name} ({dev.path})")
            except Exception as e:
                logging.warning(f"Could not initialize keyboard devices: {e}")
    
    def set_key_callback(self, key_code: int, callback: Callable[[int], None]):
        """Définit un callback pour une touche spécifique"""
        self.key_callbacks[key_code] = callback
        logging.info(f"Callback set for key code {key_code}")
    
    def set_number_key_callbacks(self, callback: Callable[[int], None]):
        """Définit des callbacks pour les touches numériques 1-6"""
        for i in range(1, 7):
            # Codes des touches numériques (rangée du haut)
            key_code = ecodes.KEY_1 + (i - 1) if EVDEV_AVAILABLE else i
            self.set_key_callback(key_code, lambda num=i: callback(num - 1))  # Index 0-5
    
    async def _monitor_keyboards(self):
        """Surveillance asynchrone des événements clavier"""
        if not EVDEV_AVAILABLE or not self.devices:
            logging.warning("No keyboard monitoring available")
            return
            
        try:
            while self.running:
                # Utilise select pour surveiller tous les périphériques
                devices_dict = {dev.fd: dev for dev in self.devices}
                
                if devices_dict:
                    r, w, x = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: evdev.util.select(devices_dict.values(), timeout=0.1)
                    )
                    
                    for fd in r:
                        device = devices_dict[fd]
                        try:
                            events = device.read()
                            for event in events:
                                if event.type == ecodes.EV_KEY and event.value == 1:  # Key press
                                    logging.debug(f"Key pressed: {event.code}")
                                    if event.code in self.key_callbacks:
                                        try:
                                            self.key_callbacks[event.code](event.code)
                                        except Exception as e:
                                            logging.error(f"Error in key callback: {e}")
                        except OSError:
                            # Périphérique déconnecté
                            logging.warning(f"Device {device.name} disconnected")
                            continue
                
                await asyncio.sleep(0.001)  # Petit délai pour éviter la surcharge CPU
                
        except Exception as e:
            logging.error(f"Error in keyboard monitoring: {e}")
    
    async def start(self):
        """Démarre la surveillance du clavier"""
        if not self.running:
            self.running = True
            logging.info("Keyboard Manager started")
            await self._monitor_keyboards()
    
    def stop(self):
        """Arrête la surveillance du clavier"""
        self.running = False
        logging.info("Keyboard Manager stopped")
    
    def list_available_keys(self):
        """Liste les codes de touches disponibles"""
        if not EVDEV_AVAILABLE:
            return {}
        
        common_keys = {
            'ESC': ecodes.KEY_ESC,
            '1': ecodes.KEY_1,
            '2': ecodes.KEY_2,
            '3': ecodes.KEY_3,
            '4': ecodes.KEY_4,
            '5': ecodes.KEY_5,
            '6': ecodes.KEY_6,
            'Q': ecodes.KEY_Q,
            'W': ecodes.KEY_W,
            'E': ecodes.KEY_E,
            'R': ecodes.KEY_R,
            'T': ecodes.KEY_T,
            'Y': ecodes.KEY_Y,
            'SPACE': ecodes.KEY_SPACE,
            'ENTER': ecodes.KEY_ENTER,
        }
        return common_keys
