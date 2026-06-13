# 🎨 Frontend Setup Guide

## Instant Browser UI (No Setup Required!)

### Option 1: Open HTML File Directly

1. **Open the interactive UI immediately:**
   ```
   Double-click: D:\dev\Kids Dev\reddit-answer-bot\INTERACTIVE_UI.html
   ```

2. **Make sure backend is running:**
   ```bash
   python main.py
   # Should show: Uvicorn running on http://0.0.0.0:8000
   ```

3. **Start typing questions!**
   - Ask anything about any topic
   - Watch the 7-agent pipeline in real-time
   - See your report in the browser

**That's it!** No npm install, no build process, just open and use.

---

## Full React App Setup (Optional)

If you want the complete React development experience:

### Step 1: Install Dependencies
```bash
cd D:\dev\Kids Dev\reddit-answer-bot\frontend
npm install
```

### Step 2: Update Agent Component

Replace the content of `src/App.tsx` with:

```typescript
import { useState, useRef, useEffect } from 'react'
import './App.css'

interface ProgressItem {
  step: string
  message: string
  details?: string
}

interface ReportData {
  id: string
  query: string
  timestamp: string
  synthesis: {
    consensus_summary: string
    confidence_score: number
    detailed_synthesis: string
  }
  perspectives: Array<{
    name: string
    consensus: string
    supporting_points: string[]
  }>
  sources: Array<{
    title: string
    url: string
    subreddit: string
  }>
}

export default function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState<ProgressItem[]>([])
  const [report, setReport] = useState<ReportData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [activeTab, setActiveTab] = useState('progress')

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [progress])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setProgress([])
    setReport(null)
    setError(null)
    setActiveTab('progress')

    try {
      const response = await fetch(
        `http://localhost:8000/api/query?q=${encodeURIComponent(query)}`
      )

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              setProgress(prev => [...prev, data])

              if (data.step === 'completed' && data.data) {
                setReport(data.data)
                setActiveTab('report')
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process query')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 shadow-lg">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            🧠 Reddit Intelligence Engine
          </h1>
          <p className="text-blue-100">
            Synthesize community consensus from Reddit discussions
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Search */}
        <form onSubmit={handleSubmit} className="mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex gap-3">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask anything about any topic..."
                className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
              >
                {loading ? '⏳ Analyzing...' : '🚀 Analyze'}
              </button>
            </div>
          </div>
        </form>

        {/* Progress & Report */}
        {progress.length > 0 && (
          <>
            <div className="mb-6 flex gap-2 border-b border-gray-700">
              <button
                onClick={() => setActiveTab('progress')}
                className={`px-4 py-2 ${
                  activeTab === 'progress'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400'
                }`}
              >
                Progress
              </button>
              {report && (
                <button
                  onClick={() => setActiveTab('report')}
                  className={`px-4 py-2 ${
                    activeTab === 'report'
                      ? 'text-blue-400 border-b-2 border-blue-400'
                      : 'text-gray-400'
                  }`}
                >
                  Report
                </button>
              )}
            </div>

            {activeTab === 'progress' && (
              <div ref={scrollRef} className="bg-gray-800 rounded-xl p-6 max-h-96 overflow-y-auto">
                {progress.map((item, idx) => (
                  <div key={idx} className="mb-3 p-3 bg-gray-700 rounded border-l-4 border-blue-500">
                    <h3 className="font-semibold text-white capitalize">{item.step}</h3>
                    <p className="text-gray-300 text-sm">{item.message}</p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {activeTab === 'report' && report && (
          <div className="space-y-6">
            <div className="bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl p-8 text-white">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">Consensus Summary</h2>
                <div className="text-right">
                  <div className="text-4xl font-bold">
                    {Math.round(report.synthesis.confidence_score * 100)}%
                  </div>
                  <div className="text-sm text-blue-100">Confidence</div>
                </div>
              </div>
              <p>{report.synthesis.consensus_summary}</p>
            </div>

            {report.perspectives && (
              <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-2xl font-bold text-white mb-4">Perspectives</h3>
                {report.perspectives.map((p, i) => (
                  <div key={i} className="mb-4 p-4 bg-gray-700 rounded border-l-4 border-green-400">
                    <h4 className="font-semibold text-white">{p.name}</h4>
                    <p className="text-gray-300 mt-1">{p.consensus}</p>
                  </div>
                ))}
              </div>
            )}

            {report.sources && (
              <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-2xl font-bold text-white mb-4">Sources</h3>
                <div className="grid grid-cols-2 gap-4">
                  {report.sources.map((s, i) => (
                    <a
                      key={i}
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="bg-gray-700 p-4 rounded hover:bg-gray-600"
                    >
                      <h4 className="font-semibold text-white">{s.title}</h4>
                      <p className="text-gray-400 text-sm">r/{s.subreddit}</p>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="bg-red-900 rounded-xl p-6 text-red-100">
            <h3 className="font-bold">Error</h3>
            <p>{error}</p>
          </div>
        )}

        {!loading && progress.length === 0 && !report && (
          <div className="text-center py-12 text-gray-300">
            <div className="text-6xl mb-4">🚀</div>
            <h2 className="text-2xl font-bold mb-2">Ready to analyze?</h2>
            <p>Ask any question about any topic</p>
          </div>
        )}
      </div>
    </div>
  )
}
```

### Step 3: Run Development Server
```bash
npm run dev
```

Your app runs on `http://localhost:5173`

---

## 🐛 Fix: Google API Deprecation Warning

The warning about `google.generativeai` being deprecated can be fixed:

### Quick Fix (Update requirements.txt)
```bash
# Change this line:
google-generativeai

# To this:
google-genai
```

Then run:
```bash
pip install --upgrade google-genai
```

### What to do next
Once installed, agents.py will work with both the old and new packages automatically (the code handles both).

---

## Usage

### Browser UI
1. Open `INTERACTIVE_UI.html` in your browser
2. Make sure backend is running: `python main.py`
3. Type your question and hit Analyze!
4. Watch real-time progress as agents execute
5. See complete report with consensus, perspectives, sources

### React App
1. Run `npm run dev`
2. Go to `http://localhost:5173`
3. Same experience as browser UI, but with full TypeScript support

---

## API Endpoints

The frontend connects to these backend endpoints:

- **GET /api/query?q=YOUR_QUESTION** - Stream SSE response with progress
- **GET /api/reports** - List all saved reports
- **GET /api/reports/{id}** - Get specific report
- **DELETE /api/reports/{id}** - Delete report

---

## Troubleshooting

### "Failed to connect to backend"
- Make sure `python main.py` is running
- Check it says: `Uvicorn running on http://0.0.0.0:8000`
- Try `http://localhost:8000` in browser to test

### UI looks broken
- Clear browser cache (Ctrl+Shift+Delete)
- Try a different browser
- Check browser console for errors (F12)

### Reports not showing
- Backend must have API key set or use simulated mode
- Check `GEMINI_API_KEY` or `GROQ_API_KEY` in `.env`

---

## 🎉 Done!

You now have a beautiful interactive UI to analyze Reddit discussions. The frontend:

✅ Streams progress in real-time  
✅ Shows all 7 agent steps  
✅ Displays final reports with full analysis  
✅ Links to source threads  
✅ Works with or without API keys  
✅ Uses Server-Sent Events for live updates  

**Just open INTERACTIVE_UI.html and start asking questions!** 🚀
