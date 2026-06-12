import sys
import os
import json
import logging

# Add parent directory to path so we can import from backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents import (
    query_expansion_agent,
    spam_and_quality_agent,
    perspective_contradiction_agent,
    knowledge_graph_agent,
    fact_checking_agent,
    consensus_synthesis_agent
)
from graph import RedditIntelligencePipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestPipeline")

def run_tests():
    logger.info("======================================")
    logger.info("Starting Backend Integration Tests")
    logger.info("======================================")

    # 1. Test Query Expansion Agent
    logger.info("Testing Agent 1: Query Expansion Agent...")
    queries = query_expansion_agent("Is a CS degree worth it?")
    logger.info(f"Generated {len(queries)} queries.")
    assert len(queries) > 0, "Query expansion returned empty list"
    logger.info(f"Queries sample: {queries[:3]}")
    logger.info("✓ Query Expansion Agent passed.")

    # 2. Test Spam and Quality Agent
    logger.info("Testing Agent 3/4: Spam and Quality Agent...")
    mock_comments = [
        {"author": "user1", "body": "Bro just buy a Mac lol", "ups": 5, "subreddit": "mac"},
        {"author": "user2", "body": "I have been using the M3 Max 128GB for running Llama 3. The unified memory makes a massive difference for local model loading.", "ups": 45, "subreddit": "LocalLLaMA"},
        {"author": "user3", "body": "[deleted]", "ups": 1, "subreddit": "LocalLLaMA"},
        {"author": "user4", "body": "Short text", "ups": 2, "subreddit": "test"}
    ]
    filtered = spam_and_quality_agent(mock_comments)
    logger.info(f"Filtered comments count: {len(filtered)}")
    assert len(filtered) > 0, "Spam filtering returned empty list"
    logger.info(f"Top comment author: {filtered[0]['author']}")
    logger.info(f"Top comment quality score: {filtered[0].get('quality_score')}")
    logger.info("✓ Spam and Quality Agent passed.")

    # 3. Test Perspective and Contradiction Extraction
    logger.info("Testing Agent 5/6: Perspective and Contradiction Extraction...")
    res = perspective_contradiction_agent("Should I buy a Tesla?", filtered)
    logger.info(f"Extracted {len(res.get('perspectives', []))} perspectives.")
    assert "perspectives" in res, "Key 'perspectives' missing from output"
    logger.info(f"Perspectives names: {[p['name'] for p in res['perspectives']]}")
    logger.info("✓ Perspective and Contradiction Extraction passed.")

    # 4. Test Knowledge Graph Agent
    logger.info("Testing Agent 7: Knowledge Graph Agent...")
    graph = knowledge_graph_agent("Should I buy a Tesla?", filtered)
    logger.info(f"Extracted {len(graph.get('nodes', []))} nodes and {len(graph.get('edges', []))} edges.")
    assert "nodes" in graph and "edges" in graph, "Knowledge graph nodes/edges missing"
    logger.info("✓ Knowledge Graph Agent passed.")

    # 5. Test Fact-Checking Agent
    logger.info("Testing Agent 9: Fact-Checking Agent...")
    facts = fact_checking_agent("Should I buy a Tesla?", filtered)
    logger.info(f"Fact-checked {len(facts)} claims.")
    if facts:
        logger.info(f"Claim 1: '{facts[0]['claim']}' Status: {facts[0]['status']}")
    logger.info("✓ Fact-Checking Agent passed.")

    # 6. Test Consensus Synthesis Agent
    logger.info("Testing Agent 8: Consensus Synthesis Agent...")
    report = consensus_synthesis_agent(
        "Should I buy a Tesla?",
        filtered,
        res.get("perspectives", []),
        res.get("contradictions", []),
        facts
    )
    logger.info("Synthesized consensus report.")
    assert "consensus_summary" in report, "Consensus summary missing"
    logger.info(f"Confidence score: {report.get('confidence_score')}")
    logger.info("✓ Consensus Synthesis Agent passed.")

    # 7. Test Full Pipeline Execution
    logger.info("Testing Full Streaming Pipeline Execution...")
    pipeline = RedditIntelligencePipeline("Is a CS degree worth it?")
    steps_run = []
    for step in pipeline.run():
        steps_run.append(step["step"])
        logger.info(f"Pipeline Step: {step['step']} - {step['message']}")
        if step["step"] == "completed":
            logger.info("Pipeline completed successfully!")
            assert "data" in step, "Completed step missing report data"
            
    logger.info(f"Steps executed: {steps_run}")
    assert "completed" in steps_run, "Pipeline failed to reach completed state"
    logger.info("✓ Full Pipeline Execution passed.")

    logger.info("======================================")
    logger.info("ALL BACKEND INTEGRATION TESTS PASSED!")
    logger.info("======================================")

if __name__ == "__main__":
    run_tests()
