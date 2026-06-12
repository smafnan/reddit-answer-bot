import React, { useState, useEffect, useRef } from 'react';

// API Base configuration
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? 'http://localhost:8000' 
  : '';

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
function ForceGraph({ graphData }: { graphData: { nodes: GraphNode[]; edges: GraphEdge[] } }) {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const width = 650;
  const height = 400;

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

        const kRepulsion = 1500;
        const kAttraction = 0.06;
        const d0 = 90; // Preferred link distance
        const gravity = 0.025; // Pull towards center
        const friction = 0.85;

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

        return updatedNodes;
      });

      animationFrameId = requestAnimationFrame(tick);
    };

    animationFrameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationFrameId);
  }, [nodes.length, edges, draggedNodeId]);

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
  const [activeTab, setActiveTab] = useState<'synthesis' | 'perspectives' | 'debates' | 'factchecks' | 'graph' | 'comments'>('synthesis');
  const [error, setError] = useState<string | null>(null);

  // Load queries history on startup
  useEffect(() => {
    loadReports();
  }, []);

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

    const encoded = encodeURIComponent(searchText);
    const eventSource = new EventSource(`${API_BASE}/api/query?q=${encoded}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.step === 'completed') {
          setActiveReport(data.data);
          setRunning(false);
          eventSource.close();
          loadReports(); // reload sidebar history
        } else if (data.step === 'failed') {
          setError(data.details || "Pipeline run failed.");
          setRunning(false);
          eventSource.close();
        } else {
          // Add/update step progress
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
  };

  const selectReport = async (id: string) => {
    setRunning(false);
    setError(null);
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

  return (
    <div className="app-container">
      {/* Background Neon Glows */}
      <div className="background-glows">
        <div className="glow-1"></div>
        <div className="glow-2"></div>
      </div>

      {/* Sidebar: Query History */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-container">
            <div className="logo-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <span className="logo-text">Reddit Intelligence</span>
          </div>
        </div>

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
              >
                <span className="report-item-query">{report.query}</span>
                <div className="report-item-meta">
                  <span>Score: {Math.round(report.confidence_score * 100)}%</span>
                  <span>{formatTimestamp(report.timestamp)}</span>
                </div>
              </div>
            ))
          )}
        </div>

        <footer className="sidebar-footer">
          <span>Engine Status: Operational (Simulated fallback active)</span>
        </footer>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        
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
                      className={`tab-btn ${activeTab === 'graph' ? 'active' : ''}`}
                      onClick={() => setActiveTab('graph')}
                    >
                      Entity Graph
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

                    {/* Tab 5: Entity Graph */}
                    {activeTab === 'graph' && (
                      <div>
                        <div style={{ marginBottom: '16px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          Drag nodes to reorganise the map. Hover nodes to view glowing relationships.
                        </div>
                        <ForceGraph graphData={activeReport.knowledge_graph} />
                      </div>
                    )}

                    {/* Tab 6: Featured Comments */}
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

              {/* Right Column: Source Threads */}
              <div className="glass-panel sources-card" style={{ height: 'fit-content', position: 'sticky', top: '40px' }}>
                <h3 className="sources-title">Verified Source Threads</h3>
                <div className="sources-list">
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
              </div>

            </div>
          </div>
        )}

      </main>
    </div>
  );
}
