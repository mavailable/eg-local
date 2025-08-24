#!/usr/bin/env python3
"""
Test de connexion MQTT vers le broker distant
"""

import asyncio
import sys
import os
from datetime import datetime

# Ajout du chemin vers les modules communs
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

try:
    from common.mqtt_async import AsyncMqtt
except ImportError:
    print("Erreur: Module MQTT non disponible. Installez les dépendances:")
    print("pip3 install paho-mqtt")
    sys.exit(1)

async def test_mqtt_connection(host="192.168.1.27", port=1883):
    print(f"=== Test de connexion MQTT ===")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Timestamp: {datetime.now()}")
    
    # Test de connexion
    client = AsyncMqtt(
        client_id="test-client",
        host=host,
        port=port
    )
    
    try:
        print("Tentative de connexion...")
        await client.connect()
        print("✓ Connexion réussie !")
        
        # Test de publication
        test_topic = "eg/test/connection"
        test_message = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "client": "test-client"
        }
        
        print(f"Publication sur {test_topic}...")
        client.publish(test_topic, test_message)
        print("✓ Publication réussie !")
        
        # Test de souscription
        def on_test_message(topic, message):
            print(f"✓ Message reçu - Topic: {topic}, Message: {message}")
        
        client.subscribe(test_topic, on_test_message)
        print(f"✓ Souscription à {test_topic} réussie !")
        
        # Attendre un peu pour recevoir le message
        await asyncio.sleep(2)
        
        print("✓ Test MQTT terminé avec succès !")
        return True
        
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        return False
    finally:
        try:
            await client.disconnect()
        except:
            pass

async def main():
    # Configuration depuis les variables d'environnement ou arguments
    host = os.getenv("CORE_HOST", "192.168.1.27")
    port = int(os.getenv("MQTT_PORT", "1883"))
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    success = await test_mqtt_connection(host, port)
    
    if success:
        print("\n🎉 La connexion MQTT fonctionne !")
        print(f"Vous pouvez maintenant utiliser CORE_HOST={host} pour vos devices")
    else:
        print("\n❌ Problème de connexion MQTT")
        print("Vérifiez que le broker MQTT est démarré sur le core:")
        print(f"  ssh pi@{host}")
        print("  cd /path/to/eg-local")
        print("  ./scripts/deploy_core.sh")

if __name__ == "__main__":
    asyncio.run(main())
