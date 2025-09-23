# Railway Deployment Troubleshooting Notes

**Date:** September 23, 2025  
**Issue:** Railway deployment failing with various errors  
**Resolution:** Successfully deployed with Google Vision API working  

## 🎯 **Final Working Solution**

### ✅ **What WORKED:**

#### **Configuration:**
- **Full `requirements.txt`** - Copied from `requirements-railway.txt` with all 70+ dependencies
- **Standard Procfile** - `web: gunicorn app:app --bind 0.0.0.0:${PORT:-8080}`
- **No Dockerfile** - Let Railway use native Python deployment
- **No nixpacks.toml** - Let Railway auto-detect Python project

#### **Environment Variables:**
- **`DATABASE_URL`** - Set to correct PostgreSQL service
- **`GOOGLE_APPLICATION_CREDENTIALS_JSON`** - Full service account JSON
- **`PORT`** - Railway auto-assigned (8080)

#### **Key Fixes:**
- **Forced rebuild** - Added timestamp comment to `requirements.txt` cleared Railway's build cache
- **Google Vision API** - Working perfectly with JSON credentials
- **Database connection** - PostgreSQL working with `psycopg2-binary`

### ❌ **What DIDN'T WORK:**

#### **Docker Approach:**
- **Dockerfile** - Railway kept failing with "pip not found" errors
- **Docker builds** - Multiple attempts failed with dependency issues
- **EXPOSE $PORT** - Build-time variable expansion caused errors

#### **Minimal Testing:**
- **Minimal requirements** - Broke the main app by removing dependencies
- **Test apps** - Railway ignored Procfile and used cached configurations
- **Simplified deployments** - Caused more problems than solutions

#### **Configuration Overrides:**
- **Procfile changes** - Railway ignored them due to cached service settings
- **Environment variables** - `RAILWAY_START_COMMAND` didn't override dashboard settings
- **NIXPACKS config** - Conflicted with Railway's auto-detection

## 🔑 **Key Lessons Learned:**

1. **Railway build cache** - Can cause dependency issues; force rebuilds when needed
2. **Full dependency set** - Don't simplify requirements.txt for testing
3. **Google Vision API** - Works great with JSON credentials in environment variables
4. **Railway dashboard** - Service settings can override code configuration
5. **Fresh builds** - Sometimes the simplest fix (timestamp comment) works best
6. **Native Python deployment** - More reliable than Docker on Railway

## 🚀 **Final Working State:**

- **Railway deployment**: ✅ Working
- **Google Vision API**: ✅ Working  
- **Image processing**: ✅ Working
- **Event generation**: ✅ Working
- **Database**: ✅ Working
- **Tesseract**: ❌ Not needed (Google Vision handles OCR)

## 📝 **Error Sequence Resolved:**

1. **`'$PORT' is not a valid port number`** → Fixed with proper environment variable handling
2. **`Application failed to respond`** → Fixed with correct DATABASE_URL
3. **`pip: command not found`** → Fixed by removing Docker approach
4. **`No module named 'flask_cors'`** → Fixed by restoring full requirements.txt
5. **`No module named 'pytz'`** → Fixed by forcing fresh build

## 🎉 **Success Metrics:**

- **Image upload working** - Users can upload images
- **Google Vision OCR** - Successfully extracting text from images
- **Event generation** - Creating events from image data
- **Database storage** - Events saved to PostgreSQL
- **Real-time processing** - Fast response times

## 🔧 **Technical Details:**

### **Google Vision API Setup:**
```python
# In scripts/image_event_processor.py
def setup_google_credentials():
    json_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if json_creds:
        creds_data = json.loads(json_creds)
        # Create temp file and set GOOGLE_APPLICATION_CREDENTIALS
```

### **Railway Environment Variables:**
- `DATABASE_URL=postgresql://postgres:...@postgres.railway.internal:5432/railway`
- `GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}`
- `PORT=8080` (auto-assigned)

### **Working Procfile:**
```
web: gunicorn app:app --bind 0.0.0.0:${PORT:-8080}
```

## 📚 **References:**

- **Railway Documentation**: https://docs.railway.app/
- **Google Vision API**: https://cloud.google.com/vision/docs
- **Flask Deployment**: https://flask.palletsprojects.com/en/2.3.x/deploying/

---

**Resolution Time:** ~4 hours  
**Key Insight:** Railway build cache was the main culprit - fresh builds solve most issues  
**Status:** ✅ Production deployment working perfectly
