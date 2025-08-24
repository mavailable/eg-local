import asyncio
import logging
from typing import Callable, Optional, Dict
try:
    import serial_asyncio
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial-asyncio not available, RFID disabled")

class RFIDManager:
    """Gestionnaire RFID asynchrone pour lecteurs série"""
    
    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.reader = None
        self.writer = None
        self.tag_callback: Optional[Callable[[str], None]] = None
        self.running = False
        self.current_tag = None
        
    def set_tag_callback(self, callback: Callable[[str], None]):
        """Définit le callback appelé lors de la détection d'un tag"""
        self.tag_callback = callback
        logging.info("RFID tag callback set")
    
    async def connect(self):
        """Connexion au lecteur RFID série"""
        if not SERIAL_AVAILABLE:
            logging.warning("Serial communication not available")
            return False
            
        try:
            self.reader, self.writer = await serial_asyncio.open_serial_connection(
                url=self.port, 
                baudrate=self.baudrate,
                timeout=1
            )
            logging.info(f"RFID reader connected on {self.port}")
            return True
        except Exception as e:
            logging.error(f"Could not connect to RFID reader: {e}")
            return False
    
    async def disconnect(self):
        """Déconnexion du lecteur RFID"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            logging.info("RFID reader disconnected")
    
    def _parse_tag_data(self, data: bytes) -> Optional[str]:
        """Parse les données du tag RFID"""
        try:
            # Conversion basique - à adapter selon le format du lecteur
            data_str = data.decode('ascii', errors='ignore').strip()
            
            # Filtrage des données valides (format hexadécimal)
            if len(data_str) >= 8 and all(c in '0123456789ABCDEFabcdef' for c in data_str):
                return data_str.upper()
            
            return None
        except Exception as e:
            logging.debug(f"Could not parse tag data: {e}")
            return None
    
    async def _monitor_rfid(self):
        """Surveillance du lecteur RFID"""
        buffer = b""
        
        while self.running and self.reader:
            try:
                # Lecture des données avec timeout
                data = await asyncio.wait_for(self.reader.read(100), timeout=0.1)
                
                if data:
                    buffer += data
                    
                    # Recherche de délimiteurs (CR/LF) pour identifier un tag complet
                    while b'\r' in buffer or b'\n' in buffer:
                        if b'\r\n' in buffer:
                            line, buffer = buffer.split(b'\r\n', 1)
                        elif b'\r' in buffer:
                            line, buffer = buffer.split(b'\r', 1)
                        else:
                            line, buffer = buffer.split(b'\n', 1)
                        
                        tag_uid = self._parse_tag_data(line)
                        if tag_uid and tag_uid != self.current_tag:
                            self.current_tag = tag_uid
                            logging.info(f"RFID tag detected: {tag_uid}")
                            
                            if self.tag_callback:
                                try:
                                    self.tag_callback(tag_uid)
                                except Exception as e:
                                    logging.error(f"Error in RFID callback: {e}")
            
            except asyncio.TimeoutError:
                # Timeout normal, continuer
                pass
            except Exception as e:
                logging.error(f"RFID monitoring error: {e}")
                await asyncio.sleep(1)
    
    async def start(self):
        """Démarre la surveillance RFID"""
        if await self.connect():
            self.running = True
            logging.info("RFID Manager started")
            await self._monitor_rfid()
        else:
            logging.error("Could not start RFID Manager")
    
    def stop(self):
        """Arrête la surveillance RFID"""
        self.running = False
        logging.info("RFID Manager stopped")
    
    async def simulate_tag(self, tag_uid: str):
        """Simule la détection d'un tag (pour tests)"""
        logging.info(f"Simulating RFID tag: {tag_uid}")
        if self.tag_callback:
            self.tag_callback(tag_uid)


class MockRFIDManager(RFIDManager):
    """Version mock du gestionnaire RFID pour développement"""
    
    def __init__(self):
        super().__init__()
        self.test_tags = ["04A37C91", "04B48D82", "04C59E73"]
        self.tag_index = 0
    
    async def connect(self):
        logging.info("Mock RFID reader connected")
        return True
    
    async def disconnect(self):
        logging.info("Mock RFID reader disconnected")
    
    async def _monitor_rfid(self):
        """Simulation de tags RFID toutes les 10 secondes"""
        while self.running:
            await asyncio.sleep(10)
            
            if self.tag_callback:
                tag_uid = self.test_tags[self.tag_index]
                self.tag_index = (self.tag_index + 1) % len(self.test_tags)
                
                logging.info(f"Mock RFID tag: {tag_uid}")
                self.tag_callback(tag_uid)
