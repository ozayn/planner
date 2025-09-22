# Railway Deployment Guide

## Environment Variables Required

Set these environment variables in Railway dashboard:

### Required
- `FLASK_ENV=production`
- `SECRET_KEY=<generate-a-secure-secret-key>`

### Database (Railway will provide automatically)
- `DATABASE_URL=<railway-postgres-url>`

### Optional API Keys (for enhanced functionality)
- `GROQ_API_KEY=<your-groq-key>`
- `OPENAI_API_KEY=<your-openai-key>`
- `ANTHROPIC_API_KEY=<your-anthropic-key>`
- `COHERE_API_KEY=<your-cohere-key>`
- `GOOGLE_API_KEY=<your-google-key>`
- `MISTRAL_API_KEY=<your-mistral-key>`
- `HUGGINGFACE_API_KEY=<your-huggingface-key>`
- `GOOGLE_MAPS_API_KEY=<your-google-maps-key>`
- `INSTAGRAM_API_KEY=<your-instagram-key>`

### Application Settings
- `MAX_VENUES_PER_CITY=2`
- `MAX_EVENTS_PER_VENUE=10`
- `DEFAULT_EVENT_TYPE=tours`
- `API_TIMEOUT=30`
- `DEBUG_MODE=false`

## Deployment Steps

1. **Install Railway CLI**:
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway**:
   ```bash
   railway login
   ```

3. **Initialize Railway project**:
   ```bash
   railway init
   ```

4. **Add PostgreSQL database**:
   ```bash
   railway add postgresql
   ```

5. **Deploy**:
   ```bash
   railway up
   ```

## Database Migration

After deployment, you'll need to run the database migration:

```bash
railway run python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## Files Created for Deployment

- `Procfile` - Defines how to start the app
- `railway.json` - Railway-specific configuration
- `runtime.txt` - Specifies Python version
- `RAILWAY_DEPLOYMENT.md` - This deployment guide
