# Quick Fix Guide: Image Processing Issues

## 🚨 **When Image Upload Stops Working**

### **Step 1: Check the Obvious (30 seconds)**
```bash
# 1. Is the app running?
curl http://localhost:5001/api/stats

# 2. Is the .env file there?
ls -la .env

# 3. Is the API key set?
grep GOOGLE_API_KEY .env
```

### **Step 2: Test LLM Directly (1 minute)**
```bash
cd /Users/oz/Dropbox/2025/planner && source venv/bin/activate
python -c "
from scripts.hybrid_event_processor import HybridEventProcessor
processor = HybridEventProcessor()
print('Gemini working:', processor.gemini_model is not None)
"
```

### **Step 3: Common Fixes (2 minutes)**

#### **Fix 1: Missing load_dotenv()**
```python
# Add to scripts/hybrid_event_processor.py
from dotenv import load_dotenv
load_dotenv()
```

#### **Fix 2: Wrong Model Name**
```python
# In _setup_gemini(), try these in order:
self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')  # Latest
self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')  # Stable
```

#### **Fix 3: Missing Import**
```python
# Add to top of hybrid_event_processor.py
import re
```

### **Step 4: Test the Fix**
```bash
python -c "
from scripts.hybrid_event_processor import HybridEventProcessor
processor = HybridEventProcessor()
result = processor._process_text_with_llm('SEP 28 | 4PM | @streetmeetdc')
print('City:', result.city)
print('Instagram:', result.instagram_handle)
"
```

## 🎯 **Root Cause Analysis**

**What Actually Broke:**
- ✅ **Fixed**: Missing `load_dotenv()` in hybrid processor
- ✅ **Fixed**: Wrong Gemini model name  
- ✅ **Fixed**: Missing `import re`

**What We Over-Engineered:**
- ❌ Complex fallback regex systems (not needed)
- ❌ Multiple model fallbacks (not needed)
- ❌ Enhanced city mappings (not needed)

## 📝 **Lessons Learned**

1. **Ask First**: "When did this stop working?" before assuming complete failure
2. **Test Simple**: Direct LLM test before building complex solutions
3. **Check Environment**: `.env` file and imports are usually the culprit
4. **One Fix at a Time**: Don't rebuild everything, fix the specific issue

## 🔧 **Emergency Commands**

```bash
# Restart app with fresh environment
pkill -f "python app.py"
source venv/bin/activate
python app.py

# Check what's actually in the logs
tail -f logs/app.log | grep -E "(ERROR|WARNING|Gemini)"
```

---
*Last Updated: September 25, 2025 - After fixing image processing regression*

