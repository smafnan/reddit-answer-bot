import React, { useState, useEffect, useRef } from 'react';

// API Base configuration
const API_BASE = (import.meta as any).env?.VITE_API_URL 
  || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:8000' 
    : '');

interface SavedReportSummary {
  id: string;
  query: string;
  timestamp: string;
  confidence_score: number;
  consensus_summary: string;
}

interface ProgressStep {
  step: string;
  message: string;
  details: string;
  expanded_queries?: string[];
}

interface SourceThread {
  title: string;
  url: string;
  subreddit: string;
}

interface FeaturedComment {
  author: string;
  body: string;
  ups: number;
  subreddit: string;
  url: string;
  quality_score: number;
  quality_reason?: string;
}

interface Perspective {
  name: string;
  consensus: string;
  supporting_points: string[];
}

interface FactCheck {
  claim: string;
  status: 'Verified' | 'Debunked' | 'Disputed' | 'Unverified';
  explanation: string;
  source_link: string;
}

interface GraphNode {
  id: string;
  label: string;
  type: string;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

interface IntelligenceReport {
  id: string;
  query: string;
  timestamp: string;
  synthesis: {
    consensus_summary: string;
    confidence_score: number;
    detailed_synthesis: string;
  };
  sources: SourceThread[];
  featured_comments: FeaturedComment[];
  perspectives: Perspective[];
  contradictions: string[];
  facts_checked: FactCheck[];
  knowledge_graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
}

// Preset Recommendations
const SEARCH_PRESETS = [
  "Best laptop for local LLMs and Ollama?",
  "Is a computer science degree worth it in 2026?",
  "Should I buy a Tesla Model Y? Owner reviews",
  "React vs Vue in 2026 tech stack choices"
];

// Interactive Physics Force-Directed Knowledge Graph Component
function ForceGraph({ graphData, floating }: { graphData: { nodes: GraphNode[]; edges: GraphEdge[] }; floating?: boolean }) {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(650);
  const height = 400;

  // Responsive width
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        if (w > 0) setWidth(Math.min(w, 650));
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Initialize positions randomly near the center
  useEffect(() => {
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) return;
    
    const initialNodes = graphData.nodes.map((node) => ({
      ...node,
      x: width / 2 + (Math.random() - 0.5) * 120,
      y: height / 2 + (Math.random() - 0.5) * 120,
      vx: 0,
      vy: 0,
    }));
    
    setNodes(initialNodes);
    setEdges(graphData.edges || []);
  }, [graphData]);

  // Physics Simulation loop
  useEffect(() => {
    if (nodes.length === 0) return;
    let animationFrameId: number;

    const tick = () => {
      setNodes((currentNodes) => {
        // Create editable copies
        const updatedNodes = currentNodes.map((node) => ({ ...node }));
        const nodeMap = new Map(updatedNodes.map((n) => [n.id, n]));

        const kRepulsion = 800;
        const kAttraction = 0.04;
        const d0 = 100;
        const gravity = 0.02;
        const friction = floating ? 0.92 : 0.85;

        // 1. Calculate repulsion forces (all pairs push apart)
        for (let i = 0; i < updatedNodes.length; i++) {
          for (let j = i + 1; j < updatedNodes.length; j++) {
            const n1 = updatedNodes[i];
            const n2 = updatedNodes[j];
            
            const dx = n2.x! - n1.x!;
            const dy = n2.y! - n1.y!;
            const distSq = dx * dx + dy * dy + 0.1;
            const dist = Math.sqrt(distSq);

            if (dist < 320) {
              const force = kRepulsion / distSq;
              const fx = (dx / dist) * force;
              const fy = (dy / dist) * force;

              if (n1.id !== draggedNodeId) {
                n1.vx! -= fx;
                n1.vy! -= fy;
              }
              if (n2.id !== draggedNodeId) {
                n2.vx! += fx;
                n2.vy! += fy;
              }
            }
          }
        }

        // 2. Calculate attraction forces (connected links pull together)
        edges.forEach((edge) => {
          // Resolve string IDs to references
          const sourceId = typeof edge.source === 'string' ? edge.source : (edge.source as any).id;
          const targetId = typeof edge.target === 'string' ? edge.target : (edge.target as any).id;
          
          const sourceNode = nodeMap.get(sourceId);
          const targetNode = nodeMap.get(targetId);

          if (sourceNode && targetNode) {
            const dx = targetNode.x! - sourceNode.x!;
            const dy = targetNode.y! - sourceNode.y!;
            const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;
            const force = kAttraction * (dist - d0);
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            if (sourceNode.id !== draggedNodeId) {
              sourceNode.vx! += fx;
              sourceNode.vy! += fy;
            }
            if (targetNode.id !== draggedNodeId) {
              targetNode.vx! -= fx;
              targetNode.vy! -= fy;
            }
          }
        });

        // 3. Center gravity, boundaries and update positions
        const cx = width / 2;
        const cy = height / 2;
        
        updatedNodes.forEach((node) => {
          if (node.id === draggedNodeId) return;

          // Pull to center (gravity)
          node.vx! += (cx - node.x!) * gravity;
          node.vy! += (cy - node.y!) * gravity;

          // Apply velocity and drag friction
          node.x! += node.vx!;
          node.y! += node.vy!;
          node.vx! *= friction;
          node.vy! *= friction;

          // Enforce boundaries
          const boundaryMargin = 30;
          if (node.x! < boundaryMargin) { node.x! = boundaryMargin; node.vx! = 0; }
          if (node.x! > width - boundaryMargin) { node.x! = width - boundaryMargin; node.vx! = 0; }
          if (node.y! < boundaryMargin) { node.y! = boundaryMargin; node.vy! = 0; }
          if (node.y! > height - boundaryMargin) { node.y! = height - boundaryMargin; node.vy! = 0; }
        });

        // 4. Gentle perpetual drift for floating mode
        if (floating) {
          updatedNodes.forEach((node) => {
            if (node.id === draggedNodeId) return;
            node.vx! += (Math.random() - 0.5) * 0.12;
            node.vy! += (Math.random() - 0.5) * 0.12;
          });
        }

        return updatedNodes;
      });

      animationFrameId = requestAnimationFrame(tick);
    };

    animationFrameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationFrameId);
  }, [nodes.length, edges, draggedNodeId, floating]);

  // Drag Handlers
  const onNodeDragStart = (id: string) => {
    setDraggedNodeId(id);
  };

  const onSvgMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!draggedNodeId || !containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setNodes((prevNodes) =>
      prevNodes.map((node) =>
        node.id === draggedNodeId
          ? { ...node, x, y, vx: 0, vy: 0 }
          : node
      )
    );
  };

  const onNodeDragEnd = () => {
    setDraggedNodeId(null);
  };

  const getNodeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'hardware': return '#f97316';     // Glowing orange
      case 'software': return '#10b981';     // Glowing green
      case 'concept': return '#0ea5e9';      // Sky blue
      case 'organization': return '#ec4899'; // Glowing pink
      default: return '#8b5cf6';             // Violet
    }
  };

  return (
    <div className="graph-viewport" ref={containerRef}>
      <svg
        className="graph-svg"
        viewBox={`0 0 ${width} ${height}`}
        onMouseMove={onSvgMouseMove}
        onMouseUp={onNodeDragEnd}
        onMouseLeave={onNodeDragEnd}
      >
        <defs>
          <marker
            id="arrowhead"
            viewBox="0 0 10 10"
            refX="18"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255, 255, 255, 0.18)" />
          </marker>
        </defs>

        {/* Render connections */}
        {edges.map((edge, i) => {
          const sId = typeof edge.source === 'string' ? edge.source : (edge.source as any).id;
          const tId = typeof edge.target === 'string' ? edge.target : (edge.target as any).id;
          
          const sNode = nodes.find((n) => n.id === sId);
          const tNode = nodes.find((n) => n.id === tId);

          if (!sNode || !tNode) return null;

          const midX = (sNode.x! + tNode.x!) / 2;
          const midY = (sNode.y! + tNode.y!) / 2;

          return (
            <g key={`edge-${i}`}>
              <line
                className="graph-edge"
                x1={sNode.x}
                y1={sNode.y}
                x2={tNode.x}
                y2={tNode.y}
                markerEnd="url(#arrowhead)"
              />
              <text
                className="graph-edge-text"
                x={midX}
                y={midY - 4}
              >
                {edge.label}
              </text>
            </g>
          );
        })}

        {/* Render nodes */}
        {nodes.map((node) => (
          <g
            key={`node-${node.id}`}
            className="graph-node"
            transform={`translate(${node.x!}, ${node.y!})`}
            onMouseDown={() => onNodeDragStart(node.id)}
          >
            <circle
              className="graph-node-circle"
              r="10"
              fill={getNodeColor(node.type)}
              stroke="rgba(255, 255, 255, 0.2)"
              style={{ color: getNodeColor(node.type) }}
            />
            <text
              className="graph-node-text"
              dx="15"
              dy="4"
            >
              {node.label}
            </text>
          </g>
        ))}
      </svg>

      <div className="graph-legend">
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#f97316' }}></div>
          <span>Hardware</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#10b981' }}></div>
          <span>Software</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#0ea5e9' }}></div>
          <span>Concept</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#ec4899' }}></div>
          <span>Organization</span>
        </div>
      </div>
    </div>
  );
}

// Main App Component
export default function App() {
  const [query, setQuery] = useState('');
  const [reports, setReports] = useState<SavedReportSummary[]>([]);
  const [activeReport, setActiveReport] = useState<IntelligenceReport | null>(null);
  const [running, setRunning] = useState(false);
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([]);
  const [activeStep, setActiveStep] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'synthesis' | 'perspectives' | 'debates' | 'factchecks' | 'comments'>('synthesis');
  const [error, setError] = useState<string | null>(null);

  // Mobile sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Collapsible sections
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sourcesCollapsed, setSourcesCollapsed] = useState(false);

  // Win98 nostalgia prompt
  const [showWin98Prompt, setShowWin98Prompt] = useState(() => {
    return localStorage.getItem('win98PromptDismissed') !== 'true';
  });

  // Theme states
  const [theme, setThemeState] = useState<'dark' | 'light' | 'win98'>(() => {
    const saved = localStorage.getItem('theme');
    return (saved === 'dark' || saved === 'light' || saved === 'win98') ? saved : 'dark';
  });

  const [startMenuOpen, setStartMenuOpen] = useState(false);
  const [clockTime, setClockTime] = useState('');
  const [win98Windows, setWin98Windows] = useState({
    search: true,
    myComputer: false,
    recycleBin: false,
    savedReports: false,
    about: false,
  });

  // Load queries history on startup
  useEffect(() => {
    loadReports();
  }, []);

  // Set theme attribute
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Digital clock timer
  useEffect(() => {
    const updateClock = () => {
      const d = new Date();
      let hours = d.getHours();
      const minutes = d.getMinutes().toString().padStart(2, '0');
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12;
      hours = hours ? hours : 12;
      setClockTime(`${hours}:${minutes} ${ampm}`);
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  const setTheme = (newTheme: 'dark' | 'light' | 'win98') => {
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  const loadReports = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/reports`);
      if (res.ok) {
        const data = await res.json();
        setReports(data);
      }
    } catch (err) {
      console.error("Failed to load historical reports", err);
    }
  };

  const deleteSingleReport = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this saved report?")) {
      try {
        const res = await fetch(`${API_BASE}/api/reports/${id}`, { method: 'DELETE' });
        if (res.ok) {
          if (activeReport?.id === id) {
            setActiveReport(null);
          }
          loadReports();
        }
      } catch (err) {
        console.error("Failed to delete report", err);
      }
    }
  };

  const clearAllSavedReports = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/reports`, { method: 'DELETE' });
      if (res.ok) {
        setActiveReport(null);
        loadReports();
        setWin98Windows(prev => ({ ...prev, recycleBin: false }));
      }
    } catch (err) {
      console.error("Failed to clear reports", err);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    triggerPipeline(query);
  };

  const triggerPipeline = (searchText: string) => {
    if (!searchText.trim()) return;
    setQuery(searchText);
    setRunning(true);
    setError(null);
    setActiveReport(null);
    setProgressSteps([]);
    setActiveStep('query_expansion');
    
    // In Win98, bring the Report/Stepper window to the front
    if (theme === 'win98') {
      setWin98Windows(p => ({ ...p, search: false }));
    }

    const encoded = encodeURIComponent(searchText);
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    if (isLocal) {
      // Local dev: use SSE streaming
      const eventSource = new EventSource(`${API_BASE}/api/query?q=${encoded}`);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.step === 'completed') {
            setActiveReport(data.data);
            setRunning(false);
            eventSource.close();
            loadReports();
          } else if (data.step === 'failed') {
            setError(data.details || "Pipeline run failed.");
            setRunning(false);
            eventSource.close();
          } else {
            setProgressSteps((prev) => {
              const idx = prev.findIndex((s) => s.step === data.step);
              if (idx !== -1) {
                const copy = [...prev];
                copy[idx] = data;
                return copy;
              } else {
                return [...prev, data];
              }
            });
            setActiveStep(data.step);
          }
        } catch (err) {
          console.error("SSE parse error", err);
        }
      };

      eventSource.onerror = (err) => {
        console.error("SSE connection error", err);
        setError("Lost connection to server stream.");
        setRunning(false);
        eventSource.close();
      };
    } else {
      // Production (Netlify/Render): use sync endpoint
      setProgressSteps([
        { step: 'query_expansion', message: 'Running analysis...', details: 'Processing your question' }
      ]);
      fetch(`${API_BASE}/api/query-sync?q=${encoded}`)
        .then(async (res) => {
          if (!res.ok) {
            const errText = await res.text();
            throw new Error(errText || `HTTP ${res.status}`);
          }
          return res.json();
        })
        .then((data) => {
          setActiveReport(data);
          setRunning(false);
          loadReports();
        })
        .catch((err) => {
          setError(err.message || "Failed to process query.");
          setRunning(false);
        });
    }
  };

  const selectReport = async (id: string) => {
    setRunning(false);
    setError(null);
    setSidebarOpen(false);
    try {
      const res = await fetch(`${API_BASE}/api/reports/${id}`);
      if (res.ok) {
        const data = await res.json();
        setActiveReport(data);
        setActiveTab('synthesis');
      } else {
        setError("Failed to fetch report.");
      }
    } catch (err) {
      console.error("Error loading report", err);
      setError("Failed to load report from server.");
    }
  };

  // Convert raw markdown strings to simple React structure
  const renderMarkdownText = (markdownStr: string) => {
    if (!markdownStr) return null;
    const lines = markdownStr.split('\n');
    return (
      <div className="detailed-synthesis-markdown">
        {lines.map((line, idx) => {
          if (line.startsWith('### ')) {
            return <h3 key={idx}>{line.slice(4)}</h3>;
          }
          if (line.startsWith('## ')) {
            return <h3 key={idx} style={{ color: 'var(--color-primary)' }}>{line.slice(3)}</h3>;
          }
          if (line.startsWith('* ') || line.startsWith('- ')) {
            return <li key={idx} style={{ marginLeft: '16px', marginBottom: '8px' }}>{line.slice(2)}</li>;
          }
          if (line.trim() === '---') {
            return <hr key={idx} />;
          }
          if (line.trim() === '') {
            return <div key={idx} style={{ height: '8px' }} />;
          }
          return <p key={idx}>{line}</p>;
        })}
      </div>
    );
  };

  const formatTimestamp = (isoStr: string) => {
    try {
      const date = new Date(isoStr);
      return date.toLocaleDateString(undefined, { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } catch {
      return isoStr;
    }
  };

  // Stepper UI Nodes Config
  const PIPELINE_NODES = [
    { key: 'query_expansion', label: 'Query Expansion Agent', desc: 'Agent 1: Generates alternative search vectors' },
    { key: 'retrieval', label: 'Reddit Retrieval Agent', desc: 'Agent 2: Scrapes comments and metadata' },
    { key: 'spam_filtering', label: 'Spam Detection Agent', desc: 'Agent 3 & 4: Filters bots, memes & scores credibility' },
    { key: 'perspective_extraction', label: 'Perspective Analysis Agent', desc: 'Agent 5 & 6: Groups consensus and disagreements' },
    { key: 'knowledge_graph_builder', label: 'Knowledge Graph Agent', desc: 'Agent 7: Maps entities and relationships' },
    { key: 'fact_checking', label: 'Fact-Check Agent', desc: 'Agent 9: Verifies technical claims against search indexes' },
    { key: 'synthesizing', label: 'Knowledge Synthesizer', desc: 'Agent 8: Formulates consensus report' },
  ];

  const getStepStatus = (nodeKey: string) => {
    const activeIndex = PIPELINE_NODES.findIndex(n => n.key === activeStep);
    const nodeIndex = PIPELINE_NODES.findIndex(n => n.key === nodeKey);

    const stepInfo = progressSteps.find((s) => s.step === nodeKey);

    if (nodeIndex < activeIndex) return { status: 'completed', info: stepInfo };
    if (nodeKey === activeStep) return { status: 'active', info: stepInfo };
    return { status: 'pending', info: null };
  };

  // ----------------- WINDOWS 98 RETRO DESKTOP LAYOUT -----------------
  if (theme === 'win98') {
    return (
      <div className="win98-desktop" style={{ width: '100vw', height: '100vh', background: '#008080', position: 'relative', overflow: 'hidden', userSelect: 'none', boxSizing: 'border-box' }}>
        
        {/* Desktop Shortcuts */}
        <div className="win98-desktop-area" style={{ position: 'absolute', top: 0, left: 0, display: 'flex', flexDirection: 'column', gap: '16px', padding: '16px', zIndex: 1 }}>
          <div className="win98-shortcut" onClick={() => setWin98Windows(p => ({ ...p, search: true }))}>
            <div className="win98-shortcut-icon" style={{ fontSize: '32px' }}>🔍</div>
            <div className="win98-shortcut-label">Search Engine</div>
          </div>
          <div className="win98-shortcut" onClick={() => setWin98Windows(p => ({ ...p, savedReports: true }))}>
            <div className="win98-shortcut-icon" style={{ fontSize: '32px' }}>📂</div>
            <div className="win98-shortcut-label">Saved Reports</div>
          </div>
          <div className="win98-shortcut" onClick={() => setWin98Windows(p => ({ ...p, myComputer: true }))}>
            <div className="win98-shortcut-icon" style={{ fontSize: '32px' }}>💻</div>
            <div className="win98-shortcut-label">My Computer</div>
          </div>
          <div className="win98-shortcut" onClick={() => setWin98Windows(p => ({ ...p, recycleBin: true }))}>
            <div className="win98-shortcut-icon" style={{ fontSize: '32px' }}>🗑️</div>
            <div className="win98-shortcut-label">Recycle Bin</div>
          </div>
        </div>

        {/* 1. Search Window */}
        {win98Windows.search && (
          <div className="glass-panel" style={{ position: 'absolute', top: '10%', left: '120px', width: '450px', zIndex: 10 }}>
            <div className="win98-frame-title">
              <span>Reddit Intelligence Search</span>
              <div className="win98-frame-btns">
                <div className="win98-frame-btn">_</div>
                <div className="win98-frame-btn">□</div>
                <div className="win98-frame-btn" onClick={() => setWin98Windows(p => ({ ...p, search: false }))}>X</div>
              </div>
            </div>
            <div>
              <p style={{ margin: '0 0 12px 0', fontSize: '11px', color: '#000' }}>
                Separate useful community knowledge from spam, bots, and hearsay. Run agentic multi-stage filters to build synthesis reports.
              </p>
              <form onSubmit={handleSearchSubmit} className="search-form">
                <div className="search-input-wrapper">
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Ask a question..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  <button type="submit" className="search-btn">Analyze</button>
                </div>
              </form>
              <div className="presets-container" style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {SEARCH_PRESETS.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="preset-btn"
                    onClick={() => {
                      setQuery(preset);
                      triggerPipeline(preset);
                    }}
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 2. Saved Investigations Window */}
        {win98Windows.savedReports && (
          <div className="glass-panel" style={{ position: 'absolute', top: '15%', left: '180px', width: '380px', zIndex: 11 }}>
            <div className="win98-frame-title">
              <span>Saved Investigations</span>
              <div className="win98-frame-btns">
                <div className="win98-frame-btn">_</div>
                <div className="win98-frame-btn">□</div>
                <div className="win98-frame-btn" onClick={() => setWin98Windows(p => ({ ...p, savedReports: false }))}>X</div>
              </div>
            </div>
            <div style={{ maxHeight: '280px', overflowY: 'auto', background: '#fff', border: '2px solid #808080', padding: '4px' }}>
              {reports.length === 0 ? (
                <div style={{ padding: '8px', fontSize: '11px', color: '#666' }}>No recent saved reports found.</div>
              ) : (
                reports.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => {
                      selectReport(r.id);
                    }}
                    style={{
                      padding: '6px',
                      borderBottom: '1px solid #e0e0e0',
                      cursor: 'pointer',
                      fontSize: '11px',
                      color: '#000',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#000080' + '15'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', width: '75%' }}>
                      <div style={{ fontWeight: 'bold' }}>{r.query}</div>
                      <div style={{ fontSize: '9px', color: '#555' }}>Score: {Math.round(r.confidence_score * 100)}% | {formatTimestamp(r.timestamp)}</div>
                    </div>
                    <button
                      onClick={(e) => deleteSingleReport(r.id, e)}
                      style={{
                        background: '#c0c0c0',
                        border: '1.5px solid',
                        borderColor: '#fff #808080 #808080 #fff',
                        padding: '1px 6px',
                        fontSize: '9px',
                        cursor: 'pointer',
                      }}
                    >
                      Delete
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* 3. Report Window (stepper or results) */}
        {(running || activeReport) && (
          <div className="glass-panel" style={{ position: 'absolute', top: '5%', left: '30%', width: '68%', height: '82%', zIndex: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div className="win98-frame-title">
              <span>{running ? `Running Analysis: ${query}` : `Report: ${activeReport?.query}`}</span>
              <div className="win98-frame-btns">
                <div className="win98-frame-btn">_</div>
                <div className="win98-frame-btn">□</div>
                <div className="win98-frame-btn" onClick={() => {
                  setRunning(false);
                  setActiveReport(null);
                }}>X</div>
              </div>
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
              {running ? (
                /* Stepper progress */
                <div className="stepper-container" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {PIPELINE_NODES.map((node) => {
                    const { status, info } = getStepStatus(node.key);
                    return (
                      <div key={node.key} className={`step-item ${status}`} style={{ display: 'flex', gap: '12px', borderBottom: '1px solid #808080', paddingBottom: '6px' }}>
                        <div className="step-node" style={{ fontWeight: 'bold', minWidth: '24px' }}>
                          {status === 'completed' && "✓"}
                          {status === 'active' && "»"}
                          {status === 'pending' && " "}
                        </div>
                        <div className="step-content">
                          <div className="step-title" style={{ fontWeight: 'bold' }}>{node.label}</div>
                          <div className="step-desc" style={{ fontSize: '10px' }}>
                            {status === 'active' || status === 'completed' 
                              ? (info?.details || info?.message || node.desc) 
                              : node.desc}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                /* Report content */
                activeReport && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div style={{ background: '#e0e0e0', border: '1px solid #808080', padding: '8px' }}>
                      <h4 style={{ margin: '0 0 4px 0', color: '#000080', fontSize: '12px' }}>Community Consensus</h4>
                      <p style={{ margin: 0, fontSize: '11px', color: '#000' }}>{activeReport.synthesis.consensus_summary}</p>
                      <div style={{ marginTop: '6px', fontSize: '10px', fontWeight: 'bold', color: '#000080' }}>
                        Confidence Level: {Math.round(activeReport.synthesis.confidence_score * 100)}%
                      </div>
                    </div>

                    <nav className="tabs-nav" style={{ display: 'flex', gap: '2px', borderBottom: '1px solid #808080', paddingBottom: '2px' }}>
                      {['synthesis', 'perspectives', 'debates', 'factchecks', 'comments'].map((tab) => (
                        <button
                          key={tab}
                          className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
                          onClick={() => setActiveTab(tab as any)}
                          style={{ fontSize: '10px', padding: '2px 8px', cursor: 'pointer' }}
                        >
                          {tab.toUpperCase()}
                        </button>
                      ))}
                    </nav>

                    <div className="tab-body" style={{ background: '#ffffff', border: '2px solid #808080', padding: '12px', minHeight: '260px', color: '#000' }}>
                      {activeTab === 'synthesis' && renderMarkdownText(activeReport.synthesis.detailed_synthesis)}
                      
                      {activeTab === 'perspectives' && (
                        <div className="perspectives-container">
                          {activeReport.perspectives.map((p, idx) => (
                            <div key={idx} style={{ border: '1px solid #808080', background: '#c0c0c0', padding: '6px', marginBottom: '8px' }}>
                              <h5 style={{ margin: '0 0 2px 0', color: '#000080', fontSize: '11px' }}>{p.name}</h5>
                              <p style={{ margin: '0 0 4px 0', fontSize: '10px' }}>{p.consensus}</p>
                              <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '10px' }}>
                                {p.supporting_points.map((pt, pIdx) => <li key={pIdx}>{pt}</li>)}
                              </ul>
                            </div>
                          ))}
                        </div>
                      )}

                      {activeTab === 'debates' && (
                        <div className="contradictions-container">
                          {activeReport.contradictions.length === 0 ? (
                            <p style={{ fontSize: '11px' }}>✓ High level of agreement. No major disputes flagged.</p>
                          ) : (
                            activeReport.contradictions.map((c, idx) => (
                              <div key={idx} style={{ border: '1px solid #808080', background: '#c0c0c0', padding: '6px', marginBottom: '6px', fontSize: '11px' }}>
                                <strong>Disputed Item #{idx + 1}:</strong> {c}
                              </div>
                            ))
                          )}
                        </div>
                      )}

                      {activeTab === 'factchecks' && (
                        <div className="factchecks-container">
                          {activeReport.facts_checked.map((f, idx) => (
                            <div key={idx} style={{ border: '1px solid #808080', background: '#c0c0c0', padding: '6px', marginBottom: '6px', fontSize: '11px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold' }}>
                                <span>{f.claim}</span>
                                <span style={{ color: f.status === 'Verified' ? '#008000' : '#800000' }}>{f.status}</span>
                              </div>
                              <p style={{ margin: '4px 0 0 0', fontSize: '10px', color: '#333' }}>{f.explanation}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {activeTab === 'comments' && (
                        <div className="comments-container">
                          {activeReport.featured_comments.map((comment, idx) => (
                            <div key={idx} style={{ borderBottom: '1px solid #808080', paddingBottom: '6px', marginBottom: '6px', fontSize: '10px' }}>
                              <div style={{ color: '#000080', fontWeight: 'bold' }}>r/{comment.subreddit} • u/{comment.author} ({comment.ups} ups)</div>
                              <p style={{ margin: '2px 0 0 0' }}>{comment.body}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Source threads links */}
                    <div>
                      <div style={{ fontWeight: 'bold', fontSize: '11px', marginBottom: '4px' }}>Source References:</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {activeReport.sources.map((s, idx) => (
                          <a
                            key={idx}
                            href={s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="preset-btn"
                            style={{ fontSize: '10px', textDecoration: 'none', color: '#000' }}
                          >
                            r/{s.subreddit}: {s.title.slice(0, 32)}...
                          </a>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              )}
            </div>
          </div>
        )}

        {/* 4. My Computer Window */}
        {win98Windows.myComputer && (
          <div className="glass-panel" style={{ position: 'absolute', top: '25%', left: '200px', width: '360px', zIndex: 13 }}>
            <div className="win98-frame-title">
              <span>My Computer - System Info</span>
              <div className="win98-frame-btns">
                <div className="win98-frame-btn">_</div>
                <div className="win98-frame-btn">□</div>
                <div className="win98-frame-btn" onClick={() => setWin98Windows(p => ({ ...p, myComputer: false }))}>X</div>
              </div>
            </div>
            <div style={{ padding: '4px', fontSize: '11px', color: '#000' }}>
              <div style={{ fontWeight: 'bold', marginBottom: '6px' }}>System Diagnostics:</div>
              <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <li>Host Platform: <strong>macOS Sandbox</strong></li>
                <li>FastAPI Backend: <span style={{ color: 'green', fontWeight: 'bold' }}>Active (Port 8000)</span></li>
                <li>Vite UI DevServer: <span style={{ color: 'green', fontWeight: 'bold' }}>Active (Port 5173)</span></li>
                <li>LLM Routing: <strong>Gemini / Groq Dual Support</strong></li>
                <li>Search Indexer: <strong>DuckDuckGo LiveFactCheck</strong></li>
                <li>Reddit Scraping: <strong>Requests-based Fallback Scraper</strong></li>
                <li>Database Directory: <strong>backend/data/</strong></li>
                <li>Total Saved Reports: <strong>{reports.length} files</strong></li>
              </ul>
            </div>
          </div>
        )}

        {/* 5. Recycle Bin Confirmation Window */}
        {win98Windows.recycleBin && (
          <div className="glass-panel" style={{ position: 'absolute', top: '30%', left: '250px', width: '320px', zIndex: 14 }}>
            <div className="win98-frame-title">
              <span>Confirm Empty Recycle Bin</span>
              <div className="win98-frame-btns">
                <div className="win98-frame-btn">_</div>
                <div className="win98-frame-btn">□</div>
                <div className="win98-frame-btn" onClick={() => setWin98Windows(p => ({ ...p, recycleBin: false }))}>X</div>
              </div>
            </div>
            <div style={{ textAlign: 'center', padding: '8px' }}>
              <p style={{ margin: '0 0 12px 0', fontSize: '11px', color: '#000' }}>
                🗑️ Are you sure you want to empty the Recycle Bin? This will delete all saved reports permanently.
              </p>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
                <button onClick={clearAllSavedReports} className="preset-btn" style={{ minWidth: '60px' }}>Yes</button>
                <button onClick={() => setWin98Windows(p => ({ ...p, recycleBin: false }))} className="preset-btn" style={{ minWidth: '60px' }}>No</button>
              </div>
            </div>
          </div>
        )}

        {/* 6. About Window */}
        {win98Windows.about && (
          <div className="glass-panel" style={{ position: 'absolute', top: '35%', left: '300px', width: '300px', zIndex: 15 }}>
            <div className="win98-frame-title">
              <span>About Reddit Intelligence Engine</span>
              <div className="win98-frame-btns">
                <div className="win98-frame-btn">_</div>
                <div className="win98-frame-btn">□</div>
                <div className="win98-frame-btn" onClick={() => setWin98Windows(p => ({ ...p, about: false }))}>X</div>
              </div>
            </div>
            <div style={{ textAlign: 'center', padding: '6px', fontSize: '11px', color: '#000' }}>
              <div style={{ fontSize: '24px', marginBottom: '6px' }}>🤖</div>
              <div style={{ fontWeight: 'bold' }}>Reddit Intelligence Engine</div>
              <div style={{ color: '#555', marginBottom: '8px' }}>v2.0 (Dual-Engine Merge)</div>
              <p style={{ margin: '0 0 12px 0', fontSize: '10px' }}>
                Powered by Gemini & Groq multi-agent Graph orchestrations, live DDG check integration, and hybrid Reddit retrievers.
              </p>
              <button onClick={() => setWin98Windows(p => ({ ...p, about: false }))} className="preset-btn" style={{ minWidth: '60px' }}>OK</button>
            </div>
          </div>
        )}

        {/* Error Dialog */}
        {error && (
          <div className="glass-panel" style={{ position: 'absolute', top: '40%', left: '320px', width: '320px', zIndex: 20 }}>
            <div className="win98-frame-title" style={{ background: 'linear-gradient(90deg, #800000, #ff0000)' }}>
              <span>Connection Error</span>
              <div className="win98-frame-btns">
                <div className="win98-frame-btn" onClick={() => setError(null)}>X</div>
              </div>
            </div>
            <div style={{ padding: '8px', fontSize: '11px', color: '#000' }}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontSize: '18px' }}>⚠️</span>
                <span>{error}</span>
              </div>
              <div style={{ marginTop: '12px', textAlign: 'right' }}>
                <button onClick={() => setError(null)} className="preset-btn" style={{ minWidth: '60px' }}>Close</button>
              </div>
            </div>
          </div>
        )}

        {/* Start Menu Popup */}
        {startMenuOpen && (
          <div className="win98-start-menu">
            <div className="win98-menu-item" onClick={() => { setWin98Windows(p => ({ ...p, search: true })); setStartMenuOpen(false); }}>🔍 Search Engine</div>
            <div className="win98-menu-item" onClick={() => { setWin98Windows(p => ({ ...p, savedReports: true })); setStartMenuOpen(false); }}>📂 Saved Reports</div>
            <div className="win98-menu-item" onClick={() => { setWin98Windows(p => ({ ...p, myComputer: true })); setStartMenuOpen(false); }}>💻 My Computer</div>
            <div className="win98-menu-item" onClick={() => { setWin98Windows(p => ({ ...p, recycleBin: true })); setStartMenuOpen(false); }}>🗑️ Recycle Bin</div>
            <div className="win98-menu-divider" />
            <div style={{ padding: '2px 8px', fontSize: '9px', color: '#808080', fontWeight: 'bold' }}>Switch Theme:</div>
            <div className="win98-menu-item" style={{ paddingLeft: '20px' }} onClick={() => { setTheme('dark'); setStartMenuOpen(false); }}>Dark Mode</div>
            <div className="win98-menu-item" style={{ paddingLeft: '20px' }} onClick={() => { setTheme('light'); setStartMenuOpen(false); }}>Light Mode</div>
            <div className="win98-menu-item" style={{ paddingLeft: '20px' }} onClick={() => { setTheme('win98'); setStartMenuOpen(false); }}>Windows 98</div>
            <div className="win98-menu-divider" />
            <div className="win98-menu-item" onClick={() => { setWin98Windows(p => ({ ...p, about: true })); setStartMenuOpen(false); }}>ℹ️ About System</div>
            <div className="win98-menu-item" onClick={() => { setTheme('dark'); setStartMenuOpen(false); }}>🛑 Shut Down</div>
          </div>
        )}

        {/* Taskbar */}
        <div className="win98-taskbar">
          <button className="win98-start-button" onClick={() => setStartMenuOpen(!startMenuOpen)}>
            <span style={{ fontSize: '13px' }}>💻</span> Start
          </button>
          
          <div className="win98-taskbar-divider" />
          
          <button className={`win98-start-button ${win98Windows.search ? 'active' : ''}`} onClick={() => setWin98Windows(p => ({ ...p, search: !p.search }))} style={{ fontWeight: 'normal', fontSize: '10px' }}>
            🔍 Search
          </button>
          <button className={`win98-start-button ${win98Windows.savedReports ? 'active' : ''}`} onClick={() => setWin98Windows(p => ({ ...p, savedReports: !p.savedReports }))} style={{ fontWeight: 'normal', fontSize: '10px' }}>
            📂 Reports
          </button>
          
          {(running || activeReport) && (
            <div className="win98-task-item" style={{ fontSize: '10px', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              📊 {running ? 'Running...' : activeReport?.query}
            </div>
          )}
          
          <div className="win98-clock">{clockTime}</div>
        </div>

      </div>
    );
  }

  // ----------------- STANDARD MODERN LAYOUT (DARK/LIGHT) -----------------
  return (
    <div className="app-container">
      {/* Background Neon Glows */}
      <div className="background-glows">
        <div className="glow-1"></div>
        <div className="glow-2"></div>
      </div>

      {/* Mobile sidebar toggle */}
      <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
        {sidebarOpen ? '✕' : '☰'}
      </button>

      {/* Sidebar backdrop */}
      <div className={`sidebar-backdrop${sidebarOpen ? ' open' : ''}`} onClick={() => setSidebarOpen(false)} />

      {/* Sidebar: Query History */}
      <aside className={`sidebar${sidebarOpen ? ' open' : ''}${sidebarCollapsed ? ' collapsed' : ''}`}>
        <div className="sidebar-header">
          <div className="logo-container">
            <div className="logo-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <span className="logo-text">Reddit Intelligence</span>
          </div>
          <button
            className="sidebar-collapse-btn"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {sidebarCollapsed
                ? <><polyline points="9 18 15 12 9 6"></polyline></>
                : <><polyline points="15 18 9 12 15 6"></polyline></>
              }
            </svg>
          </button>
        </div>

        <div className={`sidebar-collapsible${sidebarCollapsed ? ' collapsed' : ''}`}>
          <h3 className="sidebar-title">Saved Investigations</h3>

          <div className="reports-list">
          {reports.length === 0 ? (
            <div style={{ padding: '0 8px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              No recent searches found. Submit your first query to build a report.
            </div>
          ) : (
            reports.map((report) => (
              <div
                key={report.id}
                className={`report-item ${activeReport?.id === report.id ? 'active' : ''}`}
                onClick={() => selectReport(report.id)}
                style={{ position: 'relative', paddingRight: '36px' }}
              >
                <span className="report-item-query">{report.query}</span>
                <div className="report-item-meta">
                  <span>Score: {Math.round(report.confidence_score * 100)}%</span>
                  <span>{formatTimestamp(report.timestamp)}</span>
                </div>
                <button
                  onClick={(e) => deleteSingleReport(report.id, e)}
                  title="Delete Report"
                  style={{
                    position: 'absolute',
                    top: '50%',
                    right: '12px',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '4px',
                    fontSize: '0.85rem',
                    transition: 'color 0.2s',
                    zIndex: 10,
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--color-danger)'}
                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>

        <footer className="sidebar-footer" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>Engine Status: Operational</div>
          
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', borderTop: '1px solid var(--border-standard)', paddingTop: '10px' }}>
            <span>Theme:</span>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value as any)}
              style={{
                background: 'var(--bg-panel)',
                color: 'var(--text-bright)',
                border: '1px solid var(--border-standard)',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                outline: 'none',
              }}
            >
              <option value="dark">Dark Mode</option>
              <option value="light">Light Mode</option>
              <option value="win98">Windows 98</option>
            </select>
          </div>
        </footer>
        </div>{/* end sidebar-collapsible */}
      </aside>

      {/* Main Content Area */}
      <main className="main-content">

        {/* Win98 Nostalgia Prompt */}
        {showWin98Prompt && (
          <div className="win98-prompt">
            <div className="win98-prompt-content">
              <span className="win98-prompt-icon">🖥️</span>
              <span className="win98-prompt-text">Feeling nostalgic? Try <strong>Windows 98 mode</strong> for a retro experience!</span>
              <button
                className="win98-prompt-btn"
                onClick={() => {
                  setTheme('win98');
                  setShowWin98Prompt(false);
                  localStorage.setItem('win98PromptDismissed', 'true');
                }}
              >
                Enable Win98
              </button>
              <button
                className="win98-prompt-dismiss"
                onClick={() => {
                  setShowWin98Prompt(false);
                  localStorage.setItem('win98PromptDismissed', 'true');
                }}
                title="Dismiss"
              >
                ✕
              </button>
            </div>
          </div>
        )}
        
        {/* Landing Page: Search Bar */}
        {!running && !activeReport && (
          <div style={{ margin: 'auto 0' }}>
            <header className="search-header">
              <h1 className="main-title">Reddit Intelligence Engine</h1>
              <p className="sub-title">
                Separate useful community knowledge from spam, bots, and hearsay. Run agentic multi-stage filters to build synthesis reports.
              </p>
            </header>

            <div className="glass-panel" style={{ maxWidth: '800px', margin: '0 auto' }}>
              <form onSubmit={handleSearchSubmit} className="search-form">
                <div className="search-input-wrapper">
                  <div className="search-icon-left">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="11" cy="11" r="8"></circle>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                  </div>
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Ask a question (e.g. Best VRAM laptop for Ollama?)"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  <button type="submit" className="search-btn">
                    <span>Analyze</span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                  </button>
                </div>
              </form>

              <div className="presets-container">
                {SEARCH_PRESETS.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="preset-btn"
                    onClick={() => {
                      setQuery(preset);
                      triggerPipeline(preset);
                    }}
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Live Stepper View */}
        {running && (
          <div>
            <div className="glass-panel">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', borderBottom: '1px solid var(--border-standard)', paddingBottom: '16px' }}>
                <div>
                  <h2 style={{ color: 'var(--text-bright)', fontSize: '1.25rem', fontWeight: 700 }}>Executing Intelligence Pipelines</h2>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Query: "{query}"</span>
                </div>
                <div className="step-node active" style={{ animation: 'pulse-ring 2.5s infinite' }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ animation: 'spin 3s linear infinite' }}>
                    <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
                  </svg>
                </div>
              </div>

              <div className="stepper-container">
                {PIPELINE_NODES.map((node) => {
                  const { status, info } = getStepStatus(node.key);
                  return (
                    <div key={node.key} className={`step-item ${status}`}>
                      <div className="step-node">
                        {status === 'completed' && (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12"></polyline>
                          </svg>
                        )}
                        {status === 'active' && (
                          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--color-primary)' }} />
                        )}
                      </div>
                      <div className="step-content">
                        <div className="step-title">{node.label}</div>
                        <div className="step-desc">
                          {status === 'active' || status === 'completed' 
                            ? (info?.details || info?.message || node.desc) 
                            : node.desc}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="glass-panel" style={{ borderColor: 'var(--color-danger)', background: 'rgba(239, 68, 68, 0.05)' }}>
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
              <div style={{ color: 'var(--color-danger)' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
              </div>
              <div>
                <h3 style={{ color: 'var(--text-bright)', fontSize: '1rem', fontWeight: 700 }}>Connection Error</h3>
                <p style={{ fontSize: '0.85rem' }}>{error}</p>
              </div>
              <button 
                className="preset-btn" 
                style={{ marginLeft: 'auto', padding: '6px 12px' }}
                onClick={() => setError(null)}
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Results Page */}
        {activeReport && !running && (
          <div>
            {/* Header / Back Action */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
              <button
                className="preset-btn"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px' }}
                onClick={() => {
                  setActiveReport(null);
                  setQuery('');
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="19" y1="12" x2="5" y2="12"></line>
                  <polyline points="12 19 5 12 12 5"></polyline>
                </svg>
                <span>New Search</span>
              </button>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Investigation completed: {formatTimestamp(activeReport.timestamp)}
              </span>
            </div>

            <h2 className="report-query-title">Report: {activeReport.query}</h2>

            <div className="report-grid">
              
              {/* Left Column: Report Contents */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                
                {/* Consensus Summary Widget */}
                <div className="glass-panel">
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-bright)', marginBottom: '16px' }}>
                    Community Consensus
                  </h3>
                  <p className="consensus-summary-text">
                    {activeReport.synthesis.consensus_summary}
                  </p>
                  <div className="metrics-row">
                    <div className="metric-item">
                      <span className="metric-label">Confidence Score</span>
                      <div className="metric-val">
                        <span>{Math.round(activeReport.synthesis.confidence_score * 100)}%</span>
                        <div className="confidence-meter">
                          <div
                            className="confidence-bar"
                            style={{ width: `${activeReport.synthesis.confidence_score * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Entity Graph Section - Always visible between consensus and details */}
                {activeReport.knowledge_graph && activeReport.knowledge_graph.nodes && activeReport.knowledge_graph.nodes.length > 0 && (
                  <div className="glass-panel entity-graph-section">
                    <div className="entity-graph-header">
                      <h3 className="entity-graph-title">Entity Relationship Map</h3>
                      <span className="entity-graph-hint">Nodes float gently — drag to explore</span>
                    </div>
                    <ForceGraph graphData={activeReport.knowledge_graph} floating />
                  </div>
                )}

                {/* Dashboard Tabs & Contents */}
                <div className="glass-panel" style={{ padding: '24px' }}>
                  <nav className="tabs-nav">
                    <button
                      className={`tab-btn ${activeTab === 'synthesis' ? 'active' : ''}`}
                      onClick={() => setActiveTab('synthesis')}
                    >
                      Detailed Synthesis
                    </button>
                    <button
                      className={`tab-btn ${activeTab === 'perspectives' ? 'active' : ''}`}
                      onClick={() => setActiveTab('perspectives')}
                    >
                      Perspectives ({activeReport.perspectives.length})
                    </button>
                    <button
                      className={`tab-btn ${activeTab === 'debates' ? 'active' : ''}`}
                      onClick={() => setActiveTab('debates')}
                    >
                      Debates ({activeReport.contradictions.length})
                    </button>
                    <button
                      className={`tab-btn ${activeTab === 'factchecks' ? 'active' : ''}`}
                      onClick={() => setActiveTab('factchecks')}
                    >
                      Fact-Check ({activeReport.facts_checked.length})
                    </button>
                    <button
                      className={`tab-btn ${activeTab === 'comments' ? 'active' : ''}`}
                      onClick={() => setActiveTab('comments')}
                    >
                      Source Comments
                    </button>
                  </nav>

                  <div className="tab-body">
                    {/* Tab 1: Detailed Synthesis */}
                    {activeTab === 'synthesis' && (
                      <div>
                        {renderMarkdownText(activeReport.synthesis.detailed_synthesis)}
                      </div>
                    )}

                    {/* Tab 2: Perspectives */}
                    {activeTab === 'perspectives' && (
                      <div className="perspectives-container">
                        {activeReport.perspectives.length === 0 ? (
                          <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>No perspectives identified.</span>
                        ) : (
                          activeReport.perspectives.map((p, idx) => (
                            <div key={idx} className="perspective-card">
                              <h4 className="perspective-name">{p.name}</h4>
                              <p className="perspective-consensus">{p.consensus}</p>
                              <ul className="points-list">
                                {p.supporting_points.map((pt, pIdx) => (
                                  <li key={pIdx}>{pt}</li>
                                ))}
                              </ul>
                            </div>
                          ))
                        )}
                      </div>
                    )}

                    {/* Tab 3: Debates & Contradictions */}
                    {activeTab === 'debates' && (
                      <div className="contradictions-container">
                        {activeReport.contradictions.length === 0 ? (
                          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-standard)' }}>
                            <span style={{ fontSize: '0.9rem', color: 'var(--text-success)' }}>
                              ✓ The community has a high level of agreement. No major internal contradictions or debate loops were identified.
                            </span>
                          </div>
                        ) : (
                          activeReport.contradictions.map((c, idx) => (
                            <div key={idx} className="contradiction-card">
                              <h4 className="contradiction-title">Point of Disagreement #{idx + 1}</h4>
                              <p className="contradiction-body">{c}</p>
                            </div>
                          ))
                        )}
                      </div>
                    )}

                    {/* Tab 4: Fact-Check Log */}
                    {activeTab === 'factchecks' && (
                      <div className="factchecks-container">
                        {activeReport.facts_checked.length === 0 ? (
                          <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>No claims check logs available for this topic.</span>
                        ) : (
                          activeReport.facts_checked.map((f, idx) => (
                            <div key={idx} className="factcheck-card">
                              <div className="factcheck-header">
                                <span className="factcheck-claim">{f.claim}</span>
                                <span className={`factcheck-badge ${f.status.toLowerCase()}`}>
                                  {f.status}
                                </span>
                              </div>
                              <p className="factcheck-explanation">{f.explanation}</p>
                              {f.source_link && (
                                <a href={f.source_link} target="_blank" rel="noopener noreferrer" className="factcheck-source">
                                  <span>Source Reference</span>
                                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                                    <polyline points="15 3 21 3 21 9"></polyline>
                                    <line x1="10" y1="14" x2="21" y2="3"></line>
                                  </svg>
                                </a>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    )}

                    {/* Tab 5: Featured Comments */}
                    {activeTab === 'comments' && (
                      <div className="comments-container">
                        {activeReport.featured_comments.map((comment, idx) => (
                          <div key={idx} className="reddit-comment-card">
                            <div className="reddit-meta">
                              <div className="reddit-author-group">
                                <span className="reddit-subreddit">r/{comment.subreddit}</span>
                                <span>•</span>
                                <span className="reddit-author">u/{comment.author}</span>
                              </div>
                              <span className="reddit-score-tag">{comment.ups} upvotes</span>
                            </div>
                            <p className="reddit-body">{comment.body}</p>
                            {comment.quality_score !== undefined && (
                              <div className="reddit-quality-footer">
                                <span>AI Credibility Score: <span className="quality-score-badge">{Math.round(comment.quality_score * 100)}%</span></span>
                                {comment.quality_reason && <span style={{ fontStyle: 'italic', fontSize: '0.75rem' }}>"{comment.quality_reason}"</span>}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

              </div>

              {/* Right Column: Source Threads (collapsible) */}
              <div className="glass-panel sources-card" style={{ height: 'fit-content', position: 'sticky', top: '40px' }}>
                <div className="sources-header-collapsible" onClick={() => setSourcesCollapsed(!sourcesCollapsed)}>
                  <h3 className="sources-title" style={{ margin: 0 }}>Verified Source Threads</h3>
                  <button
                    className="sources-collapse-btn"
                    title={sourcesCollapsed ? 'Expand' : 'Collapse'}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      {sourcesCollapsed
                        ? <><polyline points="6 9 12 15 18 9"></polyline></>
                        : <><polyline points="18 15 12 9 6 15"></polyline></>
                      }
                    </svg>
                  </button>
                </div>
                {!sourcesCollapsed && (
                  <div className="sources-list" style={{ marginTop: '16px' }}>
                    {activeReport.sources.length === 0 ? (
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No external source threads linked.</span>
                    ) : (
                      activeReport.sources.map((s, idx) => (
                        <a
                          key={idx}
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="source-link-item"
                        >
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--text-bright)' }}>{s.title}</span>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <span className="source-sub-badge">r/{s.subreddit}</span>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Open post</span>
                            </div>
                          </div>
                        </a>
                      ))
                    )}
                  </div>
                )}
              </div>

            </div>
          </div>
        )}

      </main>
    </div>
  );
}

