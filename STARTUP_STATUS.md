# 🚀 LAW-GPT System Startup Guide

## ✅ Servers Started

Both backend and frontend servers have been started in the background.

### Backend Server (FastAPI)
- **Status**: Starting (may take 30-60 seconds to initialize RAG system)
- **URL**: http://localhost:5000
- **Health Check**: http://localhost:5000/health
- **API Docs**: http://localhost:5000/docs (Swagger UI)
- **Location**: `kaanoon_test/advanced_rag_api_server.py`

### Frontend Server (React + Vite)
- **Status**: Starting
- **URL**: http://localhost:3001
- **Location**: `frontend/` directory

## 📋 What's Happening

### Backend Initialization (30-60 seconds)
The backend is loading:
1. ✅ Advanced Agentic RAG System
2. ✅ Vector database (ChromaDB)
3. ✅ Legal document embeddings
4. ✅ Language models
5. ✅ Caching systems

### Frontend Initialization (5-10 seconds)
The frontend is:
1. ✅ Starting Vite dev server
2. ✅ Loading React components
3. ✅ Connecting to backend API

## 🔍 How to Verify

### Check Backend Status
```powershell
# Check if backend is responding
Invoke-WebRequest -Uri "http://localhost:5000/health"

# Or visit in browser:
# http://localhost:5000/docs
```

### Check Frontend Status
```powershell
# Check if frontend is responding
Invoke-WebRequest -Uri "http://localhost:3001"

# Or visit in browser:
# http://localhost:3001
```

### Check Running Processes
```powershell
# Check Python processes (backend)
Get-Process python | Where-Object {$_.Path -like "*LAW-GPT*"}

# Check Node processes (frontend)
Get-Process node | Where-Object {$_.Path -like "*LAW-GPT*"}
```

## 🎯 Next Steps

1. **Wait 30-60 seconds** for backend to fully initialize
2. **Open your browser** to http://localhost:3001
3. **Login** with any username/password (demo mode)
4. **Start using LAW-GPT**!

## 🛑 Stopping Servers

To stop the servers:

```powershell
# Stop Python processes (backend)
Get-Process python | Where-Object {$_.Path -like "*LAW-GPT*"} | Stop-Process

# Stop Node processes (frontend)
Get-Process node | Where-Object {$_.Path -like "*LAW-GPT*"} | Stop-Process
```

Or use Ctrl+C in the terminal windows where they're running.

## 📝 API Endpoints

Once backend is ready, these endpoints will be available:

- `POST /api/query` - Submit legal questions
- `GET /api/stats` - Get system statistics
- `GET /api/examples` - Get example queries
- `GET /health` - Health check
- `GET /docs` - API documentation (Swagger UI)

## 🔧 Troubleshooting

### Backend Not Starting
- Check if port 5000 is already in use
- Verify Python dependencies are installed: `pip install -r requirements.txt`
- Check logs in the terminal window

### Frontend Not Starting
- Check if port 3001 is already in use
- Verify Node modules are installed: `cd frontend && npm install`
- Check logs in the terminal window

### Connection Issues
- Ensure backend is fully initialized (wait 30-60 seconds)
- Check CORS settings in backend
- Verify API URL in frontend `.env` file

## 📞 Support

If you encounter issues:
1. Check the terminal windows for error messages
2. Verify all dependencies are installed
3. Check firewall settings
4. Review the logs in `kaanoon_test/rag_system.log`

---

**Status**: Both servers are starting. Please wait for initialization to complete.





