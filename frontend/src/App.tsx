import React, { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL
  || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : '');

const LLM_PROVIDERS: Record<string, { label: string; keyLabel: string; models: string[]; placeholder: string; link: string }> = {
  nvidia: { label: 'NVIDIA (free)', keyLabel: 'NVIDIA_API_KEY', models: ['meta/llama-3.3-70b-instruct', 'meta/llama-3.1-8b-instruct', 'nvidia/llama-3.1-nemotron-70b-instruct', 'deepseek-ai/deepseek-r1'], placeholder: 'nvapi-…', link: 'https://build.nvidia.com' },
  groq: { label: 'Groq', keyLabel: 'GROQ_API_KEY', models: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant'], placeholder: 'gsk_…', link: 'https://console.groq.com/keys' },
  gemini: { label: 'Google Gemini', keyLabel: 'GEMINI_API_KEY', models: ['gemini-2.0-flash', 'gemini-1.5-pro'], placeholder: 'AIza…', link: 'https://aistudio.google.com/app/apikey' },
  openai: { label: 'OpenAI', keyLabel: 'OPENAI_API_KEY', models: ['gpt-4o-mini', 'gpt-4o'], placeholder: 'sk-…', link: 'https://platform.openai.com/api-keys' },
  anthropic: { label: 'Anthropic', keyLabel: 'ANTHROPIC_API_KEY', models: ['claude-haiku-4-5-20251001', 'claude-sonnet-4-6'], placeholder: 'sk-ant-…', link: 'https://console.anthropic.com/settings/keys' },
};

const EXAMPLES = [
  'Is the RTX 4080 worth it for 1440p gaming?',
  'Best budget mechanical keyboard?',
  'Is a CS degree still worth it in 2026?',
  'Why does my sourdough come out dense?',
];

const STAGES = [
  { key: 'understand', label: 'Understanding your question' },
  { key: 'retrieve', label: 'Searching Reddit' },
  { key: 'answer', label: 'Reading threads & answering' },
];

interface Citation { index: number; thread_title: string; permalink: string; subreddit: string; author: string; snippet: string; ups: number; created_utc: number }
interface AnswerResponse {
  id: string; conversation_id: string; query: string; standalone_question: string; timestamp: string;
  llm_mode: 'live' | 'simulated'; provider: string | null; intent: string; grounded: boolean;
  tldr: string; answer_markdown: string; refusal_reason: string; citations: Citation[];
  sources: { title: string; url: string; subreddit: string }[]; suggested_followups: string[]; retrieval_status: string;
}
interface ChatMessage { role: 'user' | 'assistant'; content: string; answer?: AnswerResponse }
interface ProgressStep { step: string; status?: string; message: string; details: string }
interface HistoryItem { id: string; query: string; timestamp: string; tldr: string; grounded: boolean; llm_mode: string }

// ---- inline markdown with clickable [n] citation chips ----
function renderInline(text: string, onCite: (n: number) => void): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[\d+\])/g).filter(Boolean);
  return parts.map((p, i) => {
    const cite = p.match(/^\[(\d+)\]$/);
    if (cite) {
      const n = parseInt(cite[1], 10);
      return <button key={i} className="cite" onClick={() => onCite(n)} title={`Reddit source ${n}`}>{n}</button>;
    }
    if (p.startsWith('**') && p.endsWith('**')) return <strong key={i}>{p.slice(2, -2)}</strong>;
    if (p.startsWith('`') && p.endsWith('`')) return <code key={i}>{p.slice(1, -1)}</code>;
    return <React.Fragment key={i}>{p}</React.Fragment>;
  });
}

function Markdown({ text, onCite }: { text: string; onCite: (n: number) => void }) {
  const lines = (text || '').split('\n');
  const out: React.ReactNode[] = [];
  let list: React.ReactNode[] = [];
  const flush = () => { if (list.length) { out.push(<ul key={`ul-${out.length}`}>{list}</ul>); list = []; } };
  lines.forEach((line, i) => {
    if (/^#{2,3}\s/.test(line)) { flush(); out.push(<h3 key={i}>{renderInline(line.replace(/^#{2,3}\s/, ''), onCite)}</h3>); }
    else if (/^\s*[-*]\s/.test(line)) { list.push(<li key={i}>{renderInline(line.replace(/^\s*[-*]\s/, ''), onCite)}</li>); }
    else if (line.trim() === '') { flush(); }
    else { flush(); out.push(<p key={i}>{renderInline(line, onCite)}</p>); }
  });
  flush();
  return <div className="answer-body">{out}</div>;
}

function timeAgo(iso: string): string {
  try {
    const d = new Date(iso).getTime();
    const s = Math.floor((Date.now() - d) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch { return ''; }
}

function AnswerCard({ answer, onFollowup }: { answer: AnswerResponse; onFollowup: (q: string) => void }) {
  const [hl, setHl] = useState<number | null>(null);
  const onCite = useCallback((n: number) => {
    const el = document.getElementById(`src-${answer.id}-${n}`);
    if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); setHl(n); setTimeout(() => setHl(null), 1600); }
  }, [answer.id]);

  return (
    <div className={`answer-card${answer.grounded ? '' : ' refusal'}`}>
      {answer.tldr && <p className="tldr">{renderInline(answer.tldr, onCite)}</p>}
      {answer.answer_markdown && answer.answer_markdown !== answer.tldr && (
        <Markdown text={answer.answer_markdown} onCite={onCite} />
      )}

      {answer.grounded && answer.sources.length > 0 && (
        <details className="sources" open>
          <summary>▸ {answer.citations.length || answer.sources.length} Reddit source{(answer.citations.length || answer.sources.length) > 1 ? 's' : ''}</summary>
          {answer.citations.map((c) => (
            <a key={c.index} id={`src-${answer.id}-${c.index}`} className={`source${hl === c.index ? ' hl' : ''}`}
               href={c.permalink} target="_blank" rel="noopener noreferrer">
              <div className="s-head">
                <span className="s-idx">{c.index}</span>
                <span className="s-sub">r/{c.subreddit}</span>
                <span>u/{c.author}</span>
                <span>· {c.ups} upvotes</span>
              </div>
              <div className="s-snip">{c.snippet}</div>
            </a>
          ))}
        </details>
      )}

      {answer.suggested_followups.length > 0 && (
        <div className="followups">
          {answer.suggested_followups.map((f, i) => (
            <button key={i} className="followup" onClick={() => onFollowup(f)}>{f}</button>
          ))}
        </div>
      )}
    </div>
  );
}

function SettingsModal({ onClose }: { onClose: () => void }) {
  const [provider, setProvider] = usePersist('provider', 'nvidia');
  const [apiKey, setApiKey] = usePersist('apiKey', '');
  const [model, setModel] = usePersist('model', '');
  const [redditId, setRedditId] = usePersist('redditClientId', '');
  const [redditSecret, setRedditSecret] = usePersist('redditClientSecret', '');
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  const p = LLM_PROVIDERS[provider] || LLM_PROVIDERS.groq;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Settings" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div><h3>Settings</h3><p>Connect your own keys — nothing is stored on the server.</p></div>
          <button className="icon-btn" onClick={onClose} aria-label="Close settings">✕</button>
        </div>
        <div className="modal-body">
          <div className="field-label">AI model — powers understanding & answering</div>
          <div className="chips">
            {Object.entries(LLM_PROVIDERS).map(([k, v]) => (
              <button key={k} className={`chip${provider === k ? ' active' : ''}`} onClick={() => { setProvider(k); setModel(''); }}>{v.label}</button>
            ))}
          </div>
          <select className="select" value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="">Default ({p.models[0]})</option>
            {p.models.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <label className="field-label" htmlFor="k">{p.keyLabel}</label>
          <input id="k" className="input" type="password" autoComplete="off" placeholder={p.placeholder}
                 value={apiKey} onChange={(e) => setApiKey(e.target.value)} />

          <hr className="divider" />
          <div className="field-label">Reddit API — optional (improves reliability)</div>
          <p className="field-hint">
            Answers work without this by reading public Reddit directly. Adding a free “script” app from <a href="https://www.reddit.com/prefs/apps" target="_blank" rel="noopener noreferrer">reddit.com/prefs/apps</a> (redirect URI <code>http://localhost:8080</code>) makes retrieval faster and more reliable, especially under load.
          </p>
          <input className="input" type="text" autoComplete="off" placeholder="Reddit client ID (optional)"
                 value={redditId} onChange={(e) => setRedditId(e.target.value)} />
          <input className="input" type="password" autoComplete="off" placeholder="Reddit client secret (optional)"
                 value={redditSecret} onChange={(e) => setRedditSecret(e.target.value)} />

          {apiKey ? (
            <div className="status-line ok"><span>✓</span><span>Live — answering from real Reddit via <strong>{p.label}</strong>{redditId && redditSecret ? ' (using your Reddit API for reliability)' : ' (public Reddit, best-effort)'}.</span></div>
          ) : (
            <div className="status-line warn"><span>⚠</span><span>Add an AI key to go live. Without one, answers use clearly-labelled demo data for a few topics.</span></div>
          )}
          <div className="links">
            <a href={p.link} target="_blank" rel="noopener noreferrer">Get {p.label} key ↗</a>
            <a href="https://www.reddit.com/prefs/apps" target="_blank" rel="noopener noreferrer">Reddit app ↗</a>
          </div>
        </div>
      </div>
    </div>
  );
}

// localStorage-backed state
function usePersist(key: string, initial: string): [string, (v: string) => void] {
  const [v, setV] = useState<string>(() => localStorage.getItem(key) ?? initial);
  const set = useCallback((nv: string) => { setV(nv); localStorage.setItem(key, nv); }, [key]);
  return [v, set];
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [done, setDone] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = usePersist('theme', 'dark');
  const [convId, setConvId] = useState<string>(() => crypto.randomUUID());
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { document.documentElement.setAttribute('data-theme', theme); }, [theme]);
  useEffect(() => { loadHistory(); return () => abortRef.current?.abort(); }, []);
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }); }, [messages, steps, running]);

  const lastAnswer = [...messages].reverse().find((m) => m.answer)?.answer;
  const isDemo = lastAnswer ? lastAnswer.llm_mode === 'simulated' : !localStorage.getItem('apiKey');

  async function loadHistory() {
    try {
      const res = await fetch(`${API_BASE}/api/reports`);
      if (res.ok) setHistory(await res.json());
    } catch { /* offline sidebar is non-fatal */ }
  }

  function reset() {
    abortRef.current?.abort();
    setMessages([]); setSteps([]); setDone([]); setError(null); setRunning(false);
    setConvId(crypto.randomUUID()); setSidebarOpen(false);
  }

  function send(text: string) {
    const q = text.trim();
    if (!q || running) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: q }];
    setMessages(nextMessages);
    setInput(''); setError(null); setSteps([]); setDone([]); setRunning(true);

    const payload: Record<string, unknown> = {
      messages: nextMessages.map((m) => ({ role: m.role, content: m.content })),
      conversation_id: convId,
    };
    const apiKey = localStorage.getItem('apiKey');
    const provider = localStorage.getItem('provider');
    const model = localStorage.getItem('model');
    const rid = localStorage.getItem('redditClientId');
    const rsec = localStorage.getItem('redditClientSecret');
    if (apiKey) payload.api_key = apiKey;
    if (provider) payload.provider = provider;
    if (model) payload.model = model;
    if (rid && rsec) payload.reddit = { client_id: rid, client_secret: rsec };

    const onComplete = (data: AnswerResponse) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: data.tldr || data.answer_markdown, answer: data }]);
      setRunning(false); loadHistory();
    };
    const onStep = (d: ProgressStep) => {
      setSteps((prev) => { const i = prev.findIndex((s) => s.step === d.step); if (i >= 0) { const c = [...prev]; c[i] = d; return c; } return [...prev, d]; });
      if (d.status === 'done') setDone((prev) => prev.includes(d.step) ? prev : [...prev, d.step]);
    };

    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocal) {
      streamChat(payload, controller.signal, onStep, onComplete, (msg) => { setError(msg); setRunning(false); });
    } else {
      fetch(`${API_BASE}/api/chat-sync`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal: controller.signal })
        .then(async (r) => { if (!r.ok) throw new Error(await r.text() || `HTTP ${r.status}`); return r.json(); })
        .then(onComplete)
        .catch((e) => { if (e?.name !== 'AbortError') { setError(e.message || 'Request failed'); setRunning(false); } });
    }
  }

  async function streamChat(payload: unknown, signal: AbortSignal, onStep: (d: ProgressStep) => void, onComplete: (d: AnswerResponse) => void, onError: (m: string) => void) {
    try {
      const res = await fetch(`${API_BASE}/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      for (;;) {
        const { done: rdone, value } = await reader.read();
        if (rdone) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split('\n\n'); buf = parts.pop() || '';
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith('data: ')) continue;
          const d = JSON.parse(line.slice(6));
          if (d.step === 'completed') onComplete(d.data);
          else if (d.step === 'failed') onError(d.details || 'Pipeline failed');
          else onStep(d);
        }
      }
    } catch (e) {
      if ((e as Error)?.name !== 'AbortError') onError((e as Error).message || 'Connection lost');
    }
  }

  async function openHistory(id: string) {
    setSidebarOpen(false);
    try {
      const res = await fetch(`${API_BASE}/api/reports/${id}`);
      if (!res.ok) return;
      const data: AnswerResponse = await res.json();
      abortRef.current?.abort();
      setRunning(false); setSteps([]); setDone([]); setError(null);
      setConvId(data.conversation_id || crypto.randomUUID());
      setMessages([{ role: 'user', content: data.query }, { role: 'assistant', content: data.tldr, answer: data }]);
    } catch { /* ignore */ }
  }

  async function deleteHistory(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    try { await fetch(`${API_BASE}/api/reports/${id}`, { method: 'DELETE' }); loadHistory(); } catch { /* ignore */ }
  }

  function stepStatus(key: string): 'done' | 'active' | 'pending' {
    if (done.includes(key)) return 'done';
    if (running && !done.includes(key)) {
      const firstPending = STAGES.find((s) => !done.includes(s.key));
      if (firstPending?.key === key) return 'active';
    }
    return 'pending';
  }

  const empty = messages.length === 0 && !running;

  return (
    <div className="app">
      {sidebarOpen && <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar${sidebarOpen ? ' open' : ''}`}>
        <div className="sidebar-head"><span className="logo-dot">🔎</span><span>Reddit Answers</span></div>
        <button className="new-chat" onClick={reset}>＋ New chat</button>
        <div className="history">
          <div className="history-label">Recent</div>
          {history.length === 0 ? (
            <div className="history-empty">Your questions will appear here.</div>
          ) : history.map((h) => (
            <div key={h.id} className="history-item" onClick={() => openHistory(h.id)}>
              <span className="q">{h.query}</span>
              <span className="meta">{h.grounded ? '' : '⚠ '}{timeAgo(h.timestamp)}{h.llm_mode === 'simulated' ? ' · demo' : ''}</span>
              <button className="history-del" onClick={(e) => deleteHistory(h.id, e)} aria-label="Delete" title="Delete">✕</button>
            </div>
          ))}
        </div>
        <div className="sidebar-foot">
          <button className="icon-btn" onClick={() => setSettingsOpen(true)}>⚙ Settings</button>
          <button className="icon-btn" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label="Toggle theme">{theme === 'dark' ? '☀' : '☾'}</button>
        </div>
      </aside>

      <div className="main">
        <div className="topbar">
          <button className="icon-btn hamburger" onClick={() => setSidebarOpen(true)} aria-label="Menu">☰</button>
          <span className="title">Reddit Answers</span>
          <span className="spacer" />
          <span className={`badge ${isDemo ? 'demo' : 'live'}`}>{isDemo ? '○ Demo mode' : '● Live'}</span>
          <button className="icon-btn" onClick={() => setSettingsOpen(true)}>⚙</button>
        </div>

        <div className="scroll" ref={scrollRef}>
          {empty ? (
            <div className="hero">
              <h1>Ask anything.<br /><span className="grad">Answered from real Reddit.</span></h1>
              <p>A search engine that only replies from Reddit discussions — it works out what you actually mean, reads the threads, and answers with citations. If Reddit doesn’t cover it, it says so instead of guessing.</p>
              <div className="examples">
                {EXAMPLES.map((ex) => <button key={ex} className="example" onClick={() => send(ex)}>{ex}</button>)}
              </div>
            </div>
          ) : (
            <div className="thread">
              {messages.map((m, i) => (
                <div className="turn" key={i}>
                  {m.role === 'user'
                    ? <div className="user-row"><div className="user-bubble">{m.content}</div></div>
                    : m.answer && <AnswerCard answer={m.answer} onFollowup={send} />}
                </div>
              ))}
              {running && (
                <div className="stepper">
                  {STAGES.map((s) => {
                    const st = stepStatus(s.key);
                    const info = steps.find((x) => x.step === s.key);
                    return (
                      <div key={s.key} className={`step ${st}`}>
                        <span className="dot">{st === 'done' ? <span style={{ color: '#fff', fontSize: 10 }}>✓</span> : null}</span>
                        <span>{s.label}</span>
                        {info?.details && st !== 'pending' && <span className="det">{info.details}</span>}
                      </div>
                    );
                  })}
                </div>
              )}
              {error && (
                <div className="answer-card refusal">
                  <p className="tldr">Something went wrong</p>
                  <div className="answer-body"><p>{error}</p></div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="composer-wrap">
          <div className="composer">
            <div className="composer-box">
              <textarea
                ref={taRef}
                rows={1}
                placeholder={empty ? 'Ask anything…' : 'Ask a follow-up…'}
                value={input}
                onChange={(e) => { setInput(e.target.value); const t = taRef.current; if (t) { t.style.height = 'auto'; t.style.height = Math.min(t.scrollHeight, 160) + 'px'; } }}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); } }}
              />
              <button className="send" disabled={!input.trim() || running} onClick={() => send(input)} aria-label="Send">
                {running ? <span style={{ fontSize: 12 }}>■</span> : '↑'}
              </button>
            </div>
            <div className="composer-hint">
              {isDemo ? 'Demo mode — add an AI key in Settings for real, live Reddit answers.' : 'Answers are grounded only in real Reddit discussion.'}
            </div>
          </div>
        </div>
      </div>

      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
