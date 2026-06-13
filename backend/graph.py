import os
import re
import json
import logging
import uuid
import datetime
from typing import Generator, Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END

# Setup logger first (used in try-except below)
logger = logging.getLogger(__name__)

try:
    from retrieval import search_reddit_hybrid
    from agents import (
        configure_llm,
        query_expansion_agent,
        spam_and_quality_agent,
        perspective_contradiction_agent,
        knowledge_graph_agent,
        fact_checking_agent,
        consensus_synthesis_agent
    )
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    raise

# Ensure data directory exists for report persistence
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Define LangGraph Agent State
class AgentState(TypedDict):
    query: str
    expanded_queries: List[str]
    retrieved_comments: List[Dict[str, Any]]
    filtered_comments: List[Dict[str, Any]]
    perspectives: List[Dict[str, Any]]
    contradictions: List[str]
    knowledge_graph: Dict[str, Any]
    facts_checked: List[Dict[str, Any]]
    synthesis: Dict[str, Any]

# --- Nodes Implementation ---

def expand_queries_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing expand_queries_node")
    expanded = query_expansion_agent(state["query"])
    return {"expanded_queries": expanded}

def get_mock_retrieved_comments(query: str) -> List[Dict[str, Any]]:
    """Generates realistic mock retrieved comments based on the query topic."""
    query_lower = query.lower()
    is_laptop = any(w in query_lower for w in ["laptop", "macbook", "rtx", "ollama", "gpu", "vram"])
    is_tesla = any(w in query_lower for w in ["tesla", "ev", "car", "electric"])
    is_cs = any(w in query_lower for w in ["cs degree", "computer science", "career", "college", "degree", "university"])

    if is_laptop:
        return [
            {
                "post_title": "MacBook Pro M3 Max vs RTX 4090 laptop for local LLMs",
                "post_url": "https://reddit.com/r/LocalLLaMA/comments/123456",
                "subreddit": "LocalLLaMA",
                "author": "llm_dev_99",
                "ups": 142,
                "body": "I've trained ML models on both systems. Unified Memory on macOS is a game-changer for inference. A MacBook Pro with 128GB of Unified Memory can run Llama 3 70B at decent token-per-second speeds, whereas the mobile RTX 4090 only has 16GB VRAM, limiting you to 8B models. However, if you write custom CUDA kernels or do heavy PyTorch training, NVIDIA is mandatory.",
                "depth": 0,
                "created_utc": 1718112000
            },
            {
                "post_title": "MacBook Pro M3 Max vs RTX 4090 laptop for local LLMs",
                "post_url": "https://reddit.com/r/LocalLLaMA/comments/123456",
                "subreddit": "LocalLLaMA",
                "author": "cuda_coder",
                "ups": 89,
                "body": "Don't buy a laptop for heavy training; they thermal throttle in minutes and run like jets. Buy a mid-range laptop (RTX 4060) to write code, and spend the remaining $2,000 on RunPod or Paperspace. Renting an A100 is way cheaper than buying a $4,000 laptop.",
                "depth": 1,
                "created_utc": 1718115600
            },
            {
                "post_title": "Best laptop for machine learning in college?",
                "post_url": "https://reddit.com/r/LearnMachineLearning/comments/789101",
                "subreddit": "LearnMachineLearning",
                "author": "grad_student_ml",
                "ups": 56,
                "body": "If you're a student, get an RTX 4060 or 4070 Windows laptop. You need CUDA for school assignments, and Apple's MPS is sometimes a pain to configure with PyTorch libraries. Also, laptop RTX 4090 is NOT a desktop 4090, it's 40% slower and has only 16GB VRAM compared to 24GB desktop.",
                "depth": 0,
                "created_utc": 1718120000
            }
        ]
    elif is_tesla:
        return [
            {
                "post_title": "Is a Tesla Model Y worth it in 2024?",
                "post_url": "https://reddit.com/r/teslamotors/comments/111222",
                "subreddit": "teslamotors",
                "author": "ev_pioneer",
                "ups": 210,
                "body": "Model Y owner for 2 years here. The Supercharger network is the primary reason to buy a Tesla over any other EV. It's plug-and-play and incredibly reliable. The OTA software updates are great too. However, build quality is still a hit or miss—I had panel alignment issues at delivery and the cabin has some rattles.",
                "depth": 0,
                "created_utc": 1718112000
            },
            {
                "post_title": "Is a Tesla Model Y worth it in 2024?",
                "post_url": "https://reddit.com/r/teslamotors/comments/111222",
                "subreddit": "teslamotors",
                "author": "mech_guy",
                "ups": 115,
                "body": "Mechanic's perspective: Tesla restricts replacement parts to independent shops, which drives up repair times and insurance costs. Also, they depreciate incredibly fast because Tesla frequently cuts prices on new cars, killing the resale value of older models.",
                "depth": 1,
                "created_utc": 1718116000
            }
        ]
    elif is_cs:
        return [
            {
                "post_title": "Is a CS degree useless now?",
                "post_url": "https://reddit.com/r/cscareerquestions/comments/333444",
                "subreddit": "cscareerquestions",
                "author": "hiring_manager_swe",
                "ups": 320,
                "body": "A CS degree is absolutely worth it. It gets you past HR screening algorithms that instantly auto-reject bootcamp grads. It also teaches data structures, low-level OS, compilers, and database internals, which are crucial for long-term career growth. Bootcamps only teach you how to write simple React components.",
                "depth": 0,
                "created_utc": 1718112000
            },
            {
                "post_title": "Is a CS degree useless now?",
                "post_url": "https://reddit.com/r/cscareerquestions/comments/333444",
                "subreddit": "cscareerquestions",
                "author": "bootcamp_survivor",
                "ups": 182,
                "body": "Degrees are overpriced. A good portfolio, open source contributions, and solid networking can land you a job without 4 years of debt. Many universities teach outdated tech and languages no one uses in modern web dev.",
                "depth": 1,
                "created_utc": 1718115000
            }
        ]
    else:
        return [
            {
                "post_title": "General Discussion Thread",
                "post_url": "https://reddit.com/r/askreddit/comments/555666",
                "subreddit": "askreddit",
                "author": "community_voice",
                "ups": 42,
                "body": "This topic has several pros and cons. Some users recommend investing in it for long-term value, while others prefer cheaper alternatives or warn of potential pitfalls. Make sure to check reviews and compatibility before deciding.",
                "depth": 0,
                "created_utc": 1718112000
            }
        ]

def retrieve_comments_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing retrieve_comments_node")
    query = state["query"]
    expanded = state["expanded_queries"]
    
    # We query the original query + top 2 expanded queries to limit execution time
    search_list = list(set([query] + expanded[:2]))
    all_comments = []
    
    for idx, q in enumerate(search_list):
        logger.info(f"Retrieval step ({idx+1}/{len(search_list)}): searching '{q}'")
        try:
            comments = search_reddit_hybrid(q, max_results=3)
            all_comments.extend(comments)
        except Exception as e:
            logger.error(f"Error searching '{q}': {e}")
            
    # Deduplicate comments on body content
    unique_comments = []
    seen = set()
    for c in all_comments:
        body = c.get("body", "")
        if body not in seen:
            seen.add(body)
            unique_comments.append(c)
            
    # If no comments are found and Gemini client is not configured, inject realistic simulated comments
    if not unique_comments and not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        logger.info("Retrieved 0 comments in simulated mode. Injecting topic-specific mock comments.")
        unique_comments = get_mock_retrieved_comments(query)
            
    return {"retrieved_comments": unique_comments}

def filter_comments_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing filter_comments_node")
    filtered = spam_and_quality_agent(state["retrieved_comments"])
    return {"filtered_comments": filtered}

def extract_perspectives_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing extract_perspectives_node")
    data = perspective_contradiction_agent(state["query"], state["filtered_comments"])
    return {
        "perspectives": data.get("perspectives", []),
        "contradictions": data.get("contradictions", [])
    }

def build_knowledge_graph_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing build_knowledge_graph_node")
    graph_data = knowledge_graph_agent(state["query"], state["filtered_comments"])
    return {"knowledge_graph": graph_data}

def fact_check_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing fact_check_node")
    checked_facts = fact_checking_agent(state["query"], state["filtered_comments"])
    return {"facts_checked": checked_facts}

def synthesize_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Executing synthesize_node")
    report = consensus_synthesis_agent(
        query=state["query"],
        comments=state["filtered_comments"],
        perspectives=state["perspectives"],
        contradictions=state["contradictions"],
        facts=state["facts_checked"]
    )
    return {"synthesis": report}

# --- Assemble LangGraph StateGraph ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("query_expansion", expand_queries_node)
workflow.add_node("retrieval", retrieve_comments_node)
workflow.add_node("spam_filtering", filter_comments_node)
workflow.add_node("perspective_extraction", extract_perspectives_node)
workflow.add_node("knowledge_graph_builder", build_knowledge_graph_node)
workflow.add_node("fact_checking", fact_check_node)
workflow.add_node("synthesizer", synthesize_node)

# Set Flow
workflow.set_entry_point("query_expansion")
workflow.add_edge("query_expansion", "retrieval")
workflow.add_edge("retrieval", "spam_filtering")
workflow.add_edge("spam_filtering", "perspective_extraction")
workflow.add_edge("perspective_extraction", "knowledge_graph_builder")
workflow.add_edge("knowledge_graph_builder", "fact_checking")
workflow.add_edge("fact_checking", "synthesizer")
workflow.add_edge("synthesizer", END)

# Compile
compiled_graph = workflow.compile()

# --- Pipeline Class ---

class RedditIntelligencePipeline:
    """Orchestrates the multi-agent LangGraph workflow, yielding progress steps in real time."""
    
    def __init__(self, query: str, api_key: str = None, provider: str = None, model: str = None):
        self.query = query
        self.api_key = api_key
        self.provider = provider
        self.model = model

    def run(self) -> Generator[Dict[str, Any], None, None]:
        configure_llm(self.provider, self.api_key, self.model)

        # Initial State
        state = {
            "query": self.query,
            "expanded_queries": [],
            "retrieved_comments": [],
            "filtered_comments": [],
            "perspectives": [],
            "contradictions": [],
            "knowledge_graph": {"nodes": [], "edges": []},
            "facts_checked": [],
            "synthesis": {}
        }
        
        # We manually run through compiled_graph state updates, yielding friendly SSE outputs.
        # This gives us fine-grained progress steps to feed to the frontend stepper.
        
        # Step 1: Query Expansion
        yield {
            "step": "query_expansion",
            "message": "Generating alternative search angles...",
            "details": f"Analyzing query: '{self.query}'"
        }
        try:
            state.update(expand_queries_node(state))
            yield {
                "step": "retrieval",
                "message": "Querying Reddit discussions...",
                "details": f"Generated {len(state['expanded_queries'])} search angles.",
                "expanded_queries": state["expanded_queries"]
            }
        except Exception as e:
            logger.error(f"Error in query expansion step: {e}")
            state["expanded_queries"] = [self.query]
            yield {
                "step": "retrieval",
                "message": "Querying Reddit discussions...",
                "details": "Using original query (expansion failed).",
                "expanded_queries": [self.query]
            }

        # Step 2: Retrieval
        try:
            state.update(retrieve_comments_node(state))
            yield {
                "step": "spam_filtering",
                "message": "Evaluating credibility & filtering spam...",
                "details": f"Retrieved {len(state['retrieved_comments'])} unique comments across discussions."
            }
        except Exception as e:
            logger.error(f"Error in retrieval step: {e}")
            yield {
                "step": "spam_filtering",
                "message": "Evaluating credibility & filtering spam...",
                "details": "No comments retrieved. Moving to fallback."
            }

        # Step 3: Spam & Credibility Filter
        try:
            state.update(filter_comments_node(state))
            yield {
                "step": "perspective_extraction",
                "message": "Analyzing perspectives & debates...",
                "details": f"Filtered to top {len(state['filtered_comments'])} quality discussions."
            }
        except Exception as e:
            logger.error(f"Error in filtering step: {e}")
            yield {
                "step": "perspective_extraction",
                "message": "Analyzing perspectives & debates...",
                "details": "Failed to filter comments, using raw comments."
            }

        # Step 4: Perspective and Contradiction Extraction
        try:
            state.update(extract_perspectives_node(state))
            yield {
                "step": "knowledge_graph_builder",
                "message": "Constructing entity relationships...",
                "details": f"Identified {len(state['perspectives'])} distinct perspective segments."
            }
        except Exception as e:
            logger.error(f"Error in perspective extraction step: {e}")
            yield {
                "step": "knowledge_graph_builder",
                "message": "Constructing entity relationships...",
                "details": "Proceeding without perspective segmentation."
            }

        # Step 5: Knowledge Graph Construction
        try:
            state.update(build_knowledge_graph_node(state))
            yield {
                "step": "fact_checking",
                "message": "Cross-checking claims with official web sources...",
                "details": f"Extracted {len(state['knowledge_graph'].get('nodes', []))} key entity concepts."
            }
        except Exception as e:
            logger.error(f"Error in knowledge graph step: {e}")
            yield {
                "step": "fact_checking",
                "message": "Cross-checking claims with official web sources...",
                "details": "Proceeding without knowledge graph mapping."
            }

        # Step 6: Fact-Checking
        try:
            state.update(fact_check_node(state))
            yield {
                "step": "synthesizing",
                "message": "Synthesizing consensus & generating intelligence report...",
                "details": f"Fact-checked {len(state['facts_checked'])} technical assertions against web documentation."
            }
        except Exception as e:
            logger.error(f"Error in fact check step: {e}")
            yield {
                "step": "synthesizing",
                "message": "Synthesizing consensus & generating intelligence report...",
                "details": "Proceeding without active claim verification."
            }

        # Step 7: Synthesizer & Save Report
        try:
            state.update(synthesize_node(state))
            
            # Formulate final report JSON
            report_id = str(uuid.uuid4())
            slug = re.sub(r'[^a-zA-Z0-9]+', '-', self.query.lower()).strip('-')
            if not slug:
                slug = "query"
            report_filename = f"{slug}-{report_id[:8]}.json"
            report_path = os.path.join(DATA_DIR, report_filename)
            
            # Structure source threads
            seen_urls = set()
            sources = []
            for c in state["filtered_comments"]:
                url = c.get("post_url", "")
                title = c.get("post_title", "")
                sub = c.get("subreddit", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    sources.append({
                        "title": title if title else "Reddit Thread",
                        "url": url,
                        "subreddit": sub
                    })
                    
            report_data = {
                "id": report_id,
                "query": self.query,
                "timestamp": datetime.datetime.now().isoformat(),
                "synthesis": state["synthesis"],
                "sources": sources,
                "perspectives": state["perspectives"],
                "contradictions": state["contradictions"],
                "knowledge_graph": state["knowledge_graph"],
                "facts_checked": state["facts_checked"],
                "featured_comments": [
                    {
                        "author": c.get("author", "anonymous"),
                        "body": c.get("body", ""),
                        "ups": c.get("ups", 0),
                        "subreddit": c.get("subreddit", "unknown"),
                        "url": c.get("post_url", ""),
                        "quality_score": c.get("quality_score", 0.0),
                        "quality_reason": c.get("quality_reason", "")
                    }
                    for c in state["filtered_comments"][:6]
                ]
            }
            
            # Save report
            with open(report_path, "w") as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"Saved intelligence report to {report_path}")
            
            # Yield completed
            yield {
                "step": "completed",
                "message": "Synthesis complete!",
                "details": "Intelligence report compiled and saved.",
                "data": report_data
            }
        except Exception as e:
            logger.error(f"Error in synthesis and saving step: {e}")
            yield {
                "step": "failed",
                "message": "Failed to compile report.",
                "details": str(e)
            }

if __name__ == "__main__":
    pipeline = RedditIntelligencePipeline("Should I buy a Tesla?")
    for progress in pipeline.run():
        print(progress["step"], "-", progress["message"])
