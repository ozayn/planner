# 🧠 VIRTUAL ENVIRONMENT REMINDER CARD

## ⚠️ Common Error
```
ModuleNotFoundError: No module named 'dotenv'
```

## ✅ Solutions (in order of preference)

### 1. Activate Virtual Environment
```bash
source venv/bin/activate
python app.py
```

### 2. Use Convenience Script
```bash
./run.sh python app.py
```

### 3. Use Standalone Runner
```bash
python run_script.py app.py
```

### 4. Use venv Python Directly
```bash
venv/bin/python app.py
```

## 🔧 Quick Commands

```bash
# Check if venv is active
echo $VIRTUAL_ENV

# Get reminder help
./remember.sh

# Restart with venv
./restart.sh
```

## 💡 Pro Tips

- Add `source $(pwd)/shell_prompt.sh` to your ~/.bashrc for automatic reminders
- The git pre-commit hook will warn you if venv isn't active
- app.py now handles missing dotenv gracefully with helpful messages

## 🚨 Emergency Fix

If you're stuck and need to run something quickly:
```bash
python run_script.py <your_script.py>
```

