#!/bin/bash

echo "=== Test rapide du système d'entrées ==="
echo ""

# Vérification de la structure
echo "1. Vérification de la structure des fichiers..."
FILES=(
    "/home/pi/eg-local/agents/common/gpio_manager.py"
    "/home/pi/eg-local/agents/common/keyboard_manager.py"
    "/home/pi/eg-local/agents/common/rfid_manager.py"
    "/home/pi/eg-local/agents/common/input_manager.py"
    "/home/pi/eg-local/agents/slot/slot_agent.py"
    "/home/pi/eg-local/ui/slot/src/main.jsx"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (manquant)"
    fi
done

echo ""
echo "2. Test de syntaxe Python..."
cd /home/pi/eg-local/agents

# Test des imports
python3 -c "
try:
    from common.gpio_manager import GPIOManager
    from common.keyboard_manager import KeyboardManager
    from common.rfid_manager import RFIDManager
    from common.input_manager import InputManager
    print('✓ Tous les imports Python réussis')
except Exception as e:
    print(f'✗ Erreur d\'import: {e}')
"

echo ""
echo "3. Test de l'interface React..."
cd /home/pi/eg-local/ui/slot

if [ -f "package.json" ]; then
    echo "✓ package.json trouvé"
    if command -v npm &> /dev/null; then
        echo "✓ npm disponible"
        echo "  Installation des dépendances..."
        npm install --silent > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✓ Dépendances installées"
        else
            echo "✗ Erreur installation dépendances"
        fi
    else
        echo "⚠ npm non disponible"
    fi
else
    echo "✗ package.json manquant"
fi

echo ""
echo "4. Configuration suggérée pour Raspberry Pi:"
echo ""
echo "# Installation des dépendances système"
echo "sudo apt update"
echo "sudo apt install python3-pip python3-dev"
echo ""
echo "# Installation des dépendances Python"
echo "cd /home/pi/eg-local/agents"
echo "pip3 install -r requirements.txt"
echo ""
echo "# Configuration des permissions GPIO"
echo "sudo usermod -a -G gpio \$USER"
echo ""
echo "# Démarrage du système"
echo "./scripts/test_input_system.sh"

echo ""
echo "=== Test terminé ==="
