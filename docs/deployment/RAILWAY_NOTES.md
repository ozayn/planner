# Railway Deployment Notes

## 🚀 Project Details

**Project Name**: celebrated-charisma  
**Environment**: production  
**Service**: web  
**URL**: https://web-production-3b8c6c.up.railway.app/  
**Project ID**: 9ed31cc0-0716-4bc8-80aa-bcd75936f527  
**Service ID**: 1bf92398-33ca-46ab-ad80-007bb910ebc8  

## 📝 Key Commands

```bash
# Check project status
railway status

# Check deployment logs
railway logs

# Deploy updates
railway up

# Link to project (if needed)
railway link --project celebrated-charisma

# Link to service
railway service web
```

## 🔧 Deployment Configuration

**Start Command**: `python railway_data_loader.py && gunicorn app:app --bind 0.0.0.0:$PORT`

**Files Updated**:
- `railway.json` - Updated start command to include data loading
- `railway_data_loader.py` - New script to load JSON data during deployment
- `app.py` - Added export functionality for cities, venues, sources
- `templates/admin.html` - Added export buttons and JavaScript functions

## 📊 Data Loading

**Script**: `railway_data_loader.py`  
**Purpose**: Loads cities, venues, and sources from JSON files into Railway database  
**Behavior**: Only loads if database is empty (safe for multiple deployments)  

**Data Loaded**:
- Cities: 22 (from `data/cities.json`)
- Venues: 147 (from `data/venues.json`) 
- Sources: 36 (from `data/sources.json`)

## 🆕 Export Functionality

**New Features Added**:
- Export Cities from DB (`/api/admin/export-cities`)
- Export Sources from DB (`/api/admin/export-sources`)
- Updated Export Venues (`/api/admin/export-venues`)

**Export Directory**: `data/exports/` (ignored by git)

## 🐛 Known Issues & Solutions

**Issue**: Railway deployment crashed  
**Solution**: Redeployed with `railway up --service web`  
**Status**: Currently deploying (check build logs)

**Issue**: Data not loading on Railway  
**Solution**: Added `railway_data_loader.py` to start command  
**Status**: Fixed

## 📅 Deployment History

- **2025-09-16**: Initial deployment with data loader
- **2025-09-16**: Added export functionality
- **2025-09-16**: Created exports directory
- **2025-09-16**: Redeployed after crash

## 🔍 Monitoring

**Build Logs**: https://railway.com/project/9ed31cc0-0716-4bc8-80aa-bcd75936f527/service/1bf92398-33ca-46ab-ad80-007bb910ebc8

**Local App**: http://localhost:5001  
**Local Admin**: http://localhost:5001/admin

## 📋 Next Steps

1. Monitor Railway deployment completion
2. Test data loading on Railway
3. Verify cities/venues are selectable
4. Test export functionality on Railway
5. Update Railway environment variables if needed

## 🚨 Important Notes

- Railway project: `celebrated-charisma`
- Always use `--service web` flag for deployments
- Data loader runs automatically on deployment
- Export files go to `data/exports/` directory
- Local app runs on port 5001
