# AI Assistant Context

## 🎯 **Project Overview**
This is an **Event Planner App** with hybrid OCR + LLM processing for intelligent event extraction from Instagram screenshots.

## 🚨 **Critical Reminders**

### **🔑 Setup Requirements**
- **ALWAYS activate virtual environment**: `source venv/bin/activate`
- **Use port 5001**: Never use port 5000, app runs on `http://localhost:5001`
- **Use `python3`**: Not `python` (system vs venv Python)
- **Environment variables**: Add API keys to `.env` file (never commit)

### **🤖 Hybrid OCR + LLM System**
- **Smart OCR Selection**: Tesseract (local/free), Google Vision API (deployment/reliable)
- **LLM Processing**: Google Gemini for intelligent event extraction
- **Environment Detection**: Automatically chooses optimal OCR engine
- **Instagram Context**: Extracts page names, handles, poster info
- **Performance**: 90% confidence (Vision API), 80% confidence (Tesseract)

### **🌐 Deployment Status**
- **Platform**: Railway with custom domain `planner.ozayn.com`
- **Database**: PostgreSQL (Railway managed)
- **Security**: All API keys protected, no exposed credentials
- **Status**: ✅ Production ready

### **📊 Current Data**
- **Cities**: 25 loaded
- **Venues**: 178 loaded
- **Sources**: 37 loaded
- **Events**: Ready for scraping

### **🔧 Key Files**
- `scripts/hybrid_event_processor.py` - Main hybrid processing system
- `scripts/image_event_processor.py` - Original processing (fallback)
- `app.py` - Main Flask application
- `requirements.txt` - Dependencies (includes Google Gemini)

### **🎯 Recent Achievements**
- ✅ Fixed timestamp confusion (12:18 vs 4PM)
- ✅ Fixed location truncation (Island Ave → Rhode Island Ave)
- ✅ Added intelligent end time estimation (2 hours default)
- ✅ Implemented Instagram context recognition
- ✅ Created smart environment detection
- ✅ Deployed to Railway successfully

### **🚀 Next Steps**
- Test deployment at https://planner.ozayn.com
- Verify hybrid processing in production
- Monitor performance and user feedback

---
*This file provides essential context for AI assistants working on this project.*
