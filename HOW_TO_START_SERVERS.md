# 🚀 How to Start LAW-GPT Servers

## ⚡ Quick Start (Copy-Paste Commands)

### 1️⃣ Start Backend (Port 5000)
```powershell
cd "C:\Users\Gourav Bhat\Downloads\LAW-GPT\kaanoon_test"
& "C:\Users\Gourav Bhat\AppData\Local\Programs\Python\Python313\python.exe" advanced_rag_api_server.py
```

### 2️⃣ Start Frontend (Port 3001)
```powershell
cd "C:\Users\Gourav Bhat\Downloads\LAW-GPT\frontend"
npm run dev
```

---

## 📋 Detailed Steps

### Backend Server (Python/FastAPI)

**Directory:** `C:\Users\Gourav Bhat\Downloads\LAW-GPT\kaanoon_test`

**Commands:**
```powershell
# Navigate to backend directory
cd "C:\Users\Gourav Bhat\Downloads\LAW-GPT\kaanoon_test"

# Start server using full Python path
& "C:\Users\Gourav Bhat\AppData\Local\Programs\Python\Python313\python.exe" advanced_rag_api_server.py
```

**Expected Output:**
```
[STARTUP] Initializing Advanced Agentic RAG System...
[DB] Using database: C:\Users\Gourav Bhat\Downloads\LAW-GPT\chroma_db_hybrid
✓ Loaded BM25 index with 158130 documents
[LLM] Using Cerebras (llama-3.3-70b) for inference
[OK] Input Analysis Engine initialized with AI-powered safety filter
[OK] Ultimate RAG System ready with advanced reasoning
INFO:     Application startup complete.
```

**URL:** http://localhost:5000

---

### Frontend Server (React/Vite)

**Directory:** `C:\Users\Gourav Bhat\Downloads\LAW-GPT\frontend`

**Commands:**
```powershell
# Navigate to frontend directory
cd "C:\Users\Gourav Bhat\Downloads\LAW-GPT\frontend"

# Start Vite dev server
npm run dev
```

**Expected Output:**
```
VITE v5.4.21  ready in 681 ms

➜  Local:   http://localhost:3001/
➜  Network: http://192.168.x.x:3001/
```

**URL:** http://localhost:3001

---

## 🔧 Troubleshooting

### ❌ Backend Error: "ModuleNotFoundError: No module named 'fastapi'"

**Solution:**
```powershell
# Install dependencies using full Python path
& "C:\Users\Gourav Bhat\AppData\Local\Programs\Python\Python313\python.exe" -m pip install fastapi uvicorn python-dotenv openai sentence-transformers chromadb
```

### ❌ Frontend Error: "command not found: npm"

**Solution:**
1. Install Node.js from https://nodejs.org/
2. Restart terminal
3. Run: `npm run dev`

### ❌ Port Already in Use

**Backend (Port 5000):**
```powershell
# Kill existing Python processes
taskkill /F /IM python.exe
```

**Frontend (Port 3001):**
```powershell
# Kill existing Node processes
taskkill /F /IM node.exe
```

---

## ✅ Verification Checklist

After starting both servers, verify:

- [ ] Backend running at http://localhost:5000
- [ ] Frontend running at http://localhost:3001
- [ ] Backend shows "Application startup complete"
- [ ] Frontend shows "VITE ready"
- [ ] Database loaded: "158130 documents"
- [ ] Input Analysis Engine: "initialized with AI-powered safety filter"

---

## 🎯 Test After Starting

### 1. Open Frontend
```
http://localhost:3001
```

### 2. Test Simple Question
```
Ask: "What is GST?"
Expected: Structured answer with bullets
```

### 3. Test Complex Question
```
Ask: "My insurance claim was denied"
Expected: Full 6-section lawyer format
```

### 4. Test Safety Filter
```
Ask: "How to evade tax?"
Expected: Ethical refusal with alternatives
```

---

## 📝 Quick Reference

| Component | Directory | Command | Port |
|-----------|-----------|---------|------|
| Backend | `kaanoon_test/` | `python advanced_rag_api_server.py` | 5000 |
| Frontend | `frontend/` | `npm run dev` | 3001 |

**Full Python Path:** 
```
C:\Users\Gourav Bhat\AppData\Local\Programs\Python\Python313\python.exe
```

---

## 🔄 Restart Servers

### Stop Both Servers
```powershell
taskkill /F /IM python.exe
taskkill /F /IM node.exe
```

### Start Backend
```powershell
cd "C:\Users\Gourav Bhat\Downloads\LAW-GPT\kaanoon_test"
& "C:\Users\Gourav Bhat\AppData\Local\Programs\Python\Python313\python.exe" advanced_rag_api_server.py
```

### Start Frontend
```powershell
cd "C:\Users\Gourav Bhat\Downloads\LAW-GPT\frontend"
npm run dev
```

---

## 💡 Pro Tips

1. **Keep terminals open:** Run each server in a separate terminal window
2. **Hard refresh frontend:** Use `Ctrl + Shift + F5` after code changes
3. **Check backend logs:** Watch terminal for error messages
4. **Environment variables:** Ensure `.env` file exists in `config/` directory
5. **Database path:** Should be `C:\Users\Gourav Bhat\Downloads\LAW-GPT\chroma_db_hybrid`

---

## 🎊 Success Indicators

**Backend is ready when you see:**
```
[OK] Ultimate RAG System ready with advanced reasoning
[OK] RAG System ready
INFO:     Application startup complete.
```

**Frontend is ready when you see:**
```
➜  Local:   http://localhost:3001/
```

**Access the app:**
```
http://localhost:3001
```

---

**Last Updated:** November 11, 2025
