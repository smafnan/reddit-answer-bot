#!/usr/bin/env python3
"""
Test script to verify the Reddit Intelligence Engine works end-to-end.
Run this after installing dependencies: pip install -r requirements.txt
"""

import sys
import logging
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required modules can be imported."""
    logger.info("Testing imports...")
    try:
        from graph import RedditIntelligencePipeline
        from agents import (
            query_expansion_agent,
            spam_and_quality_agent,
            perspective_contradiction_agent,
            knowledge_graph_agent,
            fact_checking_agent,
            consensus_synthesis_agent
        )
        from retrieval import search_reddit_hybrid
        logger.info("✓ All imports successful")
        return True
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False

def test_query_expansion():
    """Test the query expansion agent."""
    logger.info("\nTesting query expansion agent...")
    try:
        from agents import query_expansion_agent
        queries = query_expansion_agent("best laptop for machine learning")
        logger.info(f"✓ Query expansion returned {len(queries)} queries")
        for q in queries[:3]:
            logger.info(f"  - {q}")
        return True
    except Exception as e:
        logger.error(f"✗ Query expansion failed: {e}")
        return False

def test_retrieval():
    """Test the retrieval system."""
    logger.info("\nTesting retrieval system...")
    try:
        from retrieval import search_reddit_hybrid
        results = search_reddit_hybrid("MacBook vs Windows for AI", max_results=2)
        logger.info(f"✓ Retrieval returned {len(results)} comments")
        if results:
            logger.info(f"  First comment from r/{results[0].get('subreddit')}: {results[0].get('body')[:100]}...")
        return True
    except Exception as e:
        logger.error(f"✗ Retrieval failed: {e}")
        return False

def test_full_pipeline():
    """Test the complete pipeline with a simple query."""
    logger.info("\nTesting full pipeline...")
    try:
        from graph import RedditIntelligencePipeline

        pipeline = RedditIntelligencePipeline("Is a CS degree worth it?")
        steps = 0

        for progress in pipeline.run():
            steps += 1
            logger.info(f"  Step {steps}: {progress['step']} - {progress['message']}")

            if progress['step'] == 'completed':
                logger.info("✓ Pipeline completed successfully")
                if 'data' in progress:
                    report = progress['data']
                    logger.info(f"  Report ID: {report.get('id')}")
                    synthesis = report.get('synthesis', {})
                    logger.info(f"  Confidence: {synthesis.get('confidence_score', 'N/A')}")
                return True
            elif progress['step'] == 'failed':
                logger.error(f"✗ Pipeline failed: {progress.get('details', 'Unknown error')}")
                return False

        if steps > 0:
            logger.info(f"✓ Pipeline ran through {steps} steps")
            return True
        else:
            logger.error("✗ Pipeline did not produce any steps")
            return False

    except Exception as e:
        logger.error(f"✗ Full pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agents():
    """Test individual agents."""
    logger.info("\nTesting individual agents...")

    # Mock data
    mock_comments = [
        {
            "post_title": "Test Thread",
            "post_url": "https://reddit.com/r/test/comments/123456",
            "subreddit": "test",
            "author": "test_user",
            "ups": 42,
            "body": "This is a detailed comment with technical information and benchmarks. ML models are very powerful and require GPUs for training.",
            "depth": 0,
            "created_utc": 1718112000
        }
    ]

    try:
        from agents import spam_and_quality_agent
        filtered = spam_and_quality_agent(mock_comments)
        logger.info(f"✓ Spam filter returned {len(filtered)} comments")
        return True
    except Exception as e:
        logger.error(f"✗ Agent test failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Reddit Intelligence Engine - Test Suite")
    logger.info("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Query Expansion", test_query_expansion),
        ("Retrieval System", test_retrieval),
        ("Spam Filter Agent", test_agents),
        ("Full Pipeline", test_full_pipeline),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}")
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("=" * 60)
    logger.info(f"Result: {passed_count}/{total_count} tests passed")
    logger.info("=" * 60)

    return 0 if passed_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())
