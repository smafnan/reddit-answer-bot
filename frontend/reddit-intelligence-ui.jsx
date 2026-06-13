import React, { useState, useRef, useEffect } from 'react';
import { Search, Loader, CheckCircle, AlertCircle, TrendingUp, Users, Zap } from 'lucide-react';

export default function RedditIntelligenceUI() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState([]);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);
  const [activeTab, setActiveTab] = useState('progress');

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [progress]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setProgress([]);
    setReport(null);
    setError(null);
    setActiveTab('progress');

    try {
      const response = await fetch(
        `http://localhost:8000/api/query?q=${encodeURIComponent(query)}`,
        { headers: { 'Accept': 'text/event-stream' } }
      );

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              setProgress(prev => [...prev, data]);

              if (data.step === 'completed' && data.data) {
                setReport(data.data);
                setActiveTab('report');
              } else if (data.step === 'failed') {
                setError(data.details || 'Pipeline failed');
                setActiveTab('report');
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to process query');
    } finally {
      setLoading(false);
    }
  };

  const getStepIcon = (step) => {
    const icons = {
      query_expansion: '🔍',
      retrieval: '📡',
      spam_filtering: '🛡️',
      perspective_extraction: '👥',
      knowledge_graph_builder: '🔗',
      fact_checking: '✓',
      synthesizing: '⚙️',
      completed: '✅',
      failed: '❌'
    };
    return icons[step] || '→';
  };

  const getStepColor = (step) => {
    const colors = {
      query_expansion: 'bg-blue-50 border-blue-200',
      retrieval: 'bg-purple-50 border-purple-200',
      spam_filtering: 'bg-red-50 border-red-200',
      perspective_extraction: 'bg-green-50 border-green-200',
      knowledge_graph_builder: 'bg-yellow-50 border-yellow-200',
      fact_checking: 'bg-indigo-50 border-indigo-200',
      synthesizing: 'bg-pink-50 border-pink-200',
      completed: 'bg-green-100 border-green-300',
      failed: 'bg-red-100 border-red-300'
    };
    return colors[step] || 'bg-gray-50 border-gray-200';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 shadow-lg">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            🧠 Reddit Intelligence Engine
          </h1>
          <p className="text-blue-100">
            Synthesize community consensus from Reddit discussions using AI
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Search Section */}
        <form onSubmit={handleSubmit} className="mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-4 top-3 text-gray-400" size={20} />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask anything about any topic... (e.g., 'Is a CS degree worth it?')"
                  className="w-full pl-12 pr-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none text-lg"
                  disabled={loading}
                />
              </div>
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader className="animate-spin" size={20} />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Search size={20} />
                    Analyze
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Tabs */}
        {(progress.length > 0 || report) && (
          <div className="mb-6 flex gap-2 border-b border-gray-700">
            <button
              onClick={() => setActiveTab('progress')}
              className={`px-4 py-2 font-semibold transition-colors ${
                activeTab === 'progress'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Progress ({progress.length})
            </button>
            {report && (
              <button
                onClick={() => setActiveTab('report')}
                className={`px-4 py-2 font-semibold transition-colors ${
                  activeTab === 'report'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Report
              </button>
            )}
          </div>
        )}

        {/* Progress Tab */}
        {activeTab === 'progress' && progress.length > 0 && (
          <div
            ref={scrollRef}
            className="bg-gray-800 rounded-xl shadow-lg p-6 space-y-3 max-h-96 overflow-y-auto"
          >
            {progress.map((item, idx) => (
              <div key={idx} className={`border-l-4 p-4 rounded border ${getStepColor(item.step)}`}>
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{getStepIcon(item.step)}</span>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 capitalize">
                      {item.step.replace(/_/g, ' ')}
                    </h3>
                    <p className="text-gray-700 text-sm mt-1">{item.message}</p>
                    {item.details && (
                      <p className="text-gray-600 text-xs mt-2">{item.details}</p>
                    )}
                    {item.expanded_queries && (
                      <div className="mt-2 text-xs text-gray-600">
                        <strong>Generated {item.expanded_queries.length} search angles</strong>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-3 justify-center py-4">
                <Loader className="animate-spin text-blue-400" size={24} />
                <span className="text-gray-300">Processing...</span>
              </div>
            )}
          </div>
        )}

        {/* Report Tab */}
        {activeTab === 'report' && report && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl shadow-lg p-8 text-white">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold">Consensus Summary</h2>
                <div className="text-right">
                  <div className="text-4xl font-bold">
                    {Math.round(report.synthesis.confidence_score * 100)}%
                  </div>
                  <div className="text-sm text-blue-100">Confidence</div>
                </div>
              </div>
              <p className="text-lg leading-relaxed">
                {report.synthesis.consensus_summary}
              </p>
            </div>

            {/* Perspectives */}
            {report.perspectives && report.perspectives.length > 0 && (
              <div className="bg-gray-800 rounded-xl shadow-lg p-6">
                <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <Users size={24} className="text-green-400" />
                  Key Perspectives
                </h3>
                <div className="space-y-4">
                  {report.perspectives.map((perspective, idx) => (
                    <div key={idx} className="bg-gray-700 rounded-lg p-4 border-l-4 border-green-400">
                      <h4 className="font-semibold text-white mb-2">{perspective.name}</h4>
                      <p className="text-gray-300 mb-3">{perspective.consensus}</p>
                      <ul className="text-sm text-gray-400 space-y-1">
                        {perspective.supporting_points.map((point, i) => (
                          <li key={i} className="flex gap-2">
                            <span className="text-green-400">•</span>
                            <span>{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Contradictions */}
            {report.contradictions && report.contradictions.length > 0 && (
              <div className="bg-gray-800 rounded-xl shadow-lg p-6">
                <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <AlertCircle size={24} className="text-yellow-400" />
                  Key Contradictions
                </h3>
                <div className="space-y-3">
                  {report.contradictions.map((contradiction, idx) => (
                    <div key={idx} className="bg-gray-700 rounded-lg p-4 border-l-4 border-yellow-400">
                      <p className="text-gray-200">{contradiction}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Knowledge Graph */}
            {report.knowledge_graph?.nodes && report.knowledge_graph.nodes.length > 0 && (
              <div className="bg-gray-800 rounded-xl shadow-lg p-6">
                <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <TrendingUp size={24} className="text-purple-400" />
                  Entity Relationships
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-3">Entities:</h4>
                    <div className="space-y-2">
                      {report.knowledge_graph.nodes.map((node, idx) => (
                        <div key={idx} className="bg-gray-700 rounded px-3 py-2 text-sm">
                          <span className="font-semibold text-purple-300">{node.label}</span>
                          <span className="text-gray-400 ml-2">({node.type})</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-3">Relationships:</h4>
                    <div className="space-y-2">
                      {report.knowledge_graph.edges.map((edge, idx) => (
                        <div key={idx} className="bg-gray-700 rounded px-3 py-2 text-sm text-gray-300">
                          <span className="text-purple-300">{edge.source}</span>
                          <span className="mx-2">→</span>
                          <span className="text-purple-300">{edge.target}</span>
                          <span className="block text-xs text-gray-500 mt-1">"{edge.label}"</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Fact Checks */}
            {report.facts_checked && report.facts_checked.length > 0 && (
              <div className="bg-gray-800 rounded-xl shadow-lg p-6">
                <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <CheckCircle size={24} className="text-indigo-400" />
                  Fact-Checked Claims
                </h3>
                <div className="space-y-4">
                  {report.facts_checked.map((fact, idx) => (
                    <div key={idx} className="bg-gray-700 rounded-lg p-4 border-l-4 border-indigo-400">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-semibold text-white flex-1">{fact.claim}</h4>
                        <span className={`text-xs font-bold px-2 py-1 rounded whitespace-nowrap ml-2 ${
                          fact.status === 'Verified' ? 'bg-green-900 text-green-200' :
                          fact.status === 'Debunked' ? 'bg-red-900 text-red-200' :
                          fact.status === 'Disputed' ? 'bg-yellow-900 text-yellow-200' :
                          'bg-gray-600 text-gray-200'
                        }`}>
                          {fact.status}
                        </span>
                      </div>
                      <p className="text-gray-300 text-sm mb-2">{fact.explanation}</p>
                      <a href={fact.source_link} target="_blank" rel="noopener noreferrer"
                         className="text-indigo-400 text-xs hover:text-indigo-300">
                        → Source
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sources */}
            {report.sources && report.sources.length > 0 && (
              <div className="bg-gray-800 rounded-xl shadow-lg p-6">
                <h3 className="text-xl font-bold text-white mb-4">📚 Source Threads</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {report.sources.map((source, idx) => (
                    <a
                      key={idx}
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="bg-gray-700 hover:bg-gray-600 rounded-lg p-4 transition-colors border border-gray-600 hover:border-blue-400"
                    >
                      <h4 className="font-semibold text-white mb-2 hover:text-blue-400">
                        {source.title}
                      </h4>
                      <p className="text-sm text-gray-400">
                        r/{source.subreddit}
                      </p>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Featured Comments */}
            {report.featured_comments && report.featured_comments.length > 0 && (
              <div className="bg-gray-800 rounded-xl shadow-lg p-6">
                <h3 className="text-xl font-bold text-white mb-4">💬 Featured Comments</h3>
                <div className="space-y-4">
                  {report.featured_comments.slice(0, 3).map((comment, idx) => (
                    <div key={idx} className="bg-gray-700 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-purple-300">u/{comment.author}</span>
                        <span className="text-xs text-gray-400">
                          ⬆️ {comment.ups} | Quality: {Math.round(comment.quality_score * 100)}%
                        </span>
                      </div>
                      <p className="text-gray-300 text-sm line-clamp-3">{comment.body}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Report Metadata */}
            <div className="bg-gray-800 rounded-xl shadow-lg p-4 text-center text-sm text-gray-400">
              <p>Report ID: <span className="font-mono text-gray-300">{report.id}</span></p>
              <p>Generated: {new Date(report.timestamp).toLocaleString()}</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-900 border-l-4 border-red-500 rounded-lg p-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="text-red-400 flex-shrink-0 mt-1" size={24} />
              <div>
                <h3 className="font-semibold text-red-200">Error</h3>
                <p className="text-red-100 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && progress.length === 0 && !report && (
          <div className="text-center py-12">
            <Zap className="mx-auto text-gray-500 mb-4" size={48} />
            <h2 className="text-2xl font-bold text-gray-300 mb-2">
              Ready to analyze Reddit discussions?
            </h2>
            <p className="text-gray-400 mb-6">
              Ask any question and watch the 7-agent pipeline synthesize community consensus in real-time.
            </p>
            <div className="bg-gray-800 rounded-lg p-4 inline-block text-left text-sm text-gray-300">
              <p className="font-semibold mb-2">Try questions like:</p>
              <ul className="space-y-1 text-gray-400">
                <li>• "Is a CS degree worth it?"</li>
                <li>• "Best programming language for beginners?"</li>
                <li>• "Should I buy a MacBook for development?"</li>
                <li>• "Remote vs office work - what's better?"</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
