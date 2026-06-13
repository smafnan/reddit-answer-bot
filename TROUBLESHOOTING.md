# 🔧 Troubleshooting: "Lost Connection to Server Stream"

## Quick Diagnosis

Run this to test if your backend is working:

```bash
cd D:\dev\Kids Dev\reddit-answer-bot\backend
curl http://localhost:8000/
```

You should see:
```json
{"status":"healthy","service":"Reddit Intelligence Engine API"}
```

---

## ❌ Common Issues & Fixes

### Issue 1: Backend Not Running

**Symptom**: "Connection Error - Lost connection to server stream"

**Fix**:
```bash
cd D:\dev\Kids Dev\reddit-answer-bot\backend
python main.py
```

Wait for:
```
INFO:agents:Initialized Groq client successfully.
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

If you DON'T see "Application startup complete", there's an error. Check the terminal output.

---

### Issue 2: Backend Crashes on Startup

**Symptom**: `python main.py` exits immediately with errors

**Common causes:**

#### Missing Dependencies
```bash
pip install -r requirements.txt
```

#### Python Path Issues
Make sure you're in the right directory:
```bash
cd D:\dev\Kids Dev\reddit-answer-bot\backend
python main.py
```

#### Import Errors
Check for these errors:
- `ModuleNotFoundError: No module named 'groq'` → `pip install groq`
- `ModuleNotFoundError: No module named 'fastapi'` → `pip install fastapi`
- `ModuleNotFoundError: No module named 'praw'` → `pip install praw`

---

### Issue 3: Backend Starts but Connection Drops Mid-Stream

**Symptom**: Shows progress for 2-3 steps, then "Lost connection"

**Possible causes:**

#### A. Groq API Call Fails
Check if your GROQ_API_KEY in `.env` is correct:
```
GROQ_API_KEY=gsk_YOUR_ACTUAL_KEY_HERE
```

To verify, run:
```bash
python verify_groq.py
```

You should see: ✅ SUCCESS! Everything is working!

#### B. Pipeline Crashes Mid-Execution
Check backend terminal for errors. It might show something like:
```
ERROR:agents:Error in fact_checking_agent: ...
```

If there's an error, the stream will drop.

#### C. Network/Firewall Blocking localhost:8000
Try accessing directly in browser:
```
http://localhost:8000/
```

If it shows the health status, networking is fine.

---

### Issue 4: CORS Error in Browser Console

**Symptom**: Browser console shows "CORS error"

**Note**: Our backend allows all origins, so this shouldn't happen. But if it does:

**Fix**:
1. Make sure you're running from the correct backend directory
2. Restart backend: `python main.py`
3. Try a different browser

---

## 🧪 Step-by-Step Debugging

### Step 1: Test Backend Health
```bash
# In terminal
curl http://localhost:8000/
```

Should return:
```json
{"status":"healthy","service":"Reddit Intelligence Engine API"}
```

### Step 2: Test Query Endpoint (No Streaming)
```bash
# This will start processing but you won't see output yet
curl -N http://localhost:8000/api/query?q=test
```

Should show data lines like: `data: {"step":"query_expansion"...}`

### Step 3: Use Debug UI
Open: `DEBUG_UI.html`

Click "Test Connection" button. It will:
- ✅ Test basic health check
- ✅ Send a test query
- ✅ Stream the response
- ✅ Show detailed logs

This pinpoints exactly where the problem is.

### Step 4: Check Backend Logs
Look at the terminal where you ran `python main.py`:
- Look for `ERROR:` lines
- Look for exceptions
- Look for `Traceback` sections

These show what went wrong.

---

## 🚀 Complete Fresh Start

If nothing works, do a complete restart:

### 1. Kill the backend
Close the terminal running `python main.py` (or Ctrl+C)

### 2. Clear any cached files
```bash
cd D:\dev\Kids Dev\reddit-answer-bot\backend
del /s /q __pycache__
del /s /q *.pyc
```

### 3. Reinstall dependencies
```bash
pip install -r requirements.txt --force-reinstall
```

### 4. Verify Groq
```bash
python verify_groq.py
```

Should show: ✅ SUCCESS!

### 5. Start fresh
```bash
python main.py
```

### 6. Test in browser
Open: `INTERACTIVE_UI.html` or `DEBUG_UI.html`

---

## 📋 Checklist Before Testing

- ✅ Backend runs: `python main.py`
- ✅ Shows "Application startup complete"
- ✅ Shows "Initialized Groq client successfully"
- ✅ `.env` has correct `GROQ_API_KEY`
- ✅ `http://localhost:8000/` responds with health status
- ✅ Frontend can reach backend at localhost:8000

---

## 🆘 If Still Not Working

**Collect this info:**
1. What error message do you see?
2. What does the backend terminal show?
3. Does `curl http://localhost:8000/` work?
4. Does `python verify_groq.py` show SUCCESS?

Then try:
```bash
# Restart backend with verbose output
python main.py --log-level debug
```

This will show more detailed logs of what's happening.

---

## 💡 Pro Tips

### Terminal 1: Backend
```bash
cd D:\dev\Kids Dev\reddit-answer-bot\backend
python main.py
```
Keep this running. Watch it for errors.

### Terminal 2: Testing
```bash
cd D:\dev\Kids Dev\reddit-answer-bot\backend
curl http://localhost:8000/
curl http://localhost:8000/api/query?q=test
```

### Browser: Frontend
Open `INTERACTIVE_UI.html` or `DEBUG_UI.html`

This setup lets you see everything that's happening.

---

## Final Check

Your system should show:

**Backend terminal:**
```
INFO:agents:Initialized Groq client successfully.
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
INFO:     Received query request: Is a CS degree worth it?
INFO:root:Executing expand_queries_node
INFO:root:Executing retrieve_comments_node
...
```

**Browser:**
```
📊 Progress (7 steps)
🔍 query_expansion - Generating alternative search angles...
📡 retrieval - Querying Reddit discussions...
🛡️ spam_filtering - Evaluating credibility & filtering spam...
...
✅ completed - Synthesis complete!
```

If you see both, everything is working! 🎉

