#!/bin/bash
# Remember script - reminds you about virtual environment activation

echo "🧠 REMINDER: Virtual Environment Activation"
echo "=========================================="
echo ""
echo "⚠️  If you get 'ModuleNotFoundError: No module named dotenv':"
echo ""
echo "   SOLUTION 1: Activate virtual environment"
echo "   source venv/bin/activate"
echo ""
echo "   SOLUTION 2: Use convenience script"
echo "   ./run.sh python <script>"
echo ""
echo "   SOLUTION 3: Use standalone runner"
echo "   python run_script.py <script>"
echo ""
echo "   SOLUTION 4: Use venv Python directly"
echo "   venv/bin/python <script>"
echo ""
echo "💡 TIP: Add this to your shell profile for automatic reminders:"
echo "   echo 'source $(pwd)/shell_prompt.sh' >> ~/.bashrc"
echo ""
echo "🔧 Current status:"
if [[ "$VIRTUAL_ENV" == *"/planner/venv"* ]]; then
    echo "   ✅ Virtual environment is ACTIVE"
else
    echo "   ❌ Virtual environment is NOT active"
    echo "   Run: source venv/bin/activate"
fi

