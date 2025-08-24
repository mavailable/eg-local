#!/usr/bin/env python3
"""
Exemple simple d'utilisation du système d'entrées GPIO/Clavier/RFID
"""

import asyncio
import sys
import os

# Ajout du chemin vers les modules communs
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

from common.input_manager import InputManager

async def main():
    print("=== Démonstration du système d'entrées ===")
    print("Configuration de test avec mock (dev_mode=True)")
    
    # Configuration
    device_id = "demo-device"
    mqtt_host = "localhost"
    mqtt_port = 1883
    
    # Création du gestionnaire d'entrées
    input_manager = InputManager(
        device_id=device_id,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        dev_mode=True  # Mode développement avec mocks
    )
    
    print(f"Device ID: {device_id}")
    print(f"MQTT: {mqtt_host}:{mqtt_port}")
    print("")
    print("Actions disponibles:")
    print("- Touches 1-6 : Toggle LEDs 0-5")
    print("- Boutons GPIO (simulés) : Toggle LEDs correspondantes")
    print("- Tags RFID (simulés) : Affichage automatique")
    print("")
    print("Topics MQTT publiés:")
    print(f"- eg/dev/{device_id}/input/leds : État des LEDs")
    print(f"- eg/dev/{device_id}/input/rfid : Tags RFID détectés")
    print(f"- eg/dev/{device_id}/input/status : Statut du système")
    print("")
    print("Topics MQTT écoutés:")
    print(f"- eg/dev/{device_id}/input/cmd/led : Commandes LEDs")
    print(f"- eg/dev/{device_id}/input/cmd/test : Commandes de test")
    print("")
    print("Démarrage du système...")
    
    try:
        # Démarrage du gestionnaire d'entrées
        await input_manager.start()
    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"Erreur: {e}")
    finally:
        input_manager.stop()
        print("Système arrêté")

if __name__ == "__main__":
    asyncio.run(main())
