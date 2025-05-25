#!/usr/bin/env python3
"""
Test script to demonstrate browser session management performance benefits.
"""

import time
import logging
import sys
from google_shopping_scraper.scraper import GoogleShoppingScraper


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)


def test_multiple_queries_without_session_management():
    """Test multiple queries without browser session management"""
    logger = setup_logging()
    logger.info("=== Testing WITHOUT browser session management ===")
    
    queries = ["laptop", "smartphone", "headphones"]
    scraper = GoogleShoppingScraper(logger=logger, fast_mode=True, keep_browser_open=False)
    
    start_time = time.time()
    
    for i, query in enumerate(queries, 1):
        logger.info(f"Query {i}/{len(queries)}: {query}")
        query_start = time.time()
        
        items = scraper.get_shopping_data_for_query(query, headless=True)
        
        query_time = time.time() - query_start
        logger.info(f"Query '{query}' completed in {query_time:.2f} seconds, found {len(items)} items")
    
    total_time = time.time() - start_time
    logger.info(f"Total time WITHOUT session management: {total_time:.2f} seconds")
    
    return total_time


def test_multiple_queries_with_session_management():
    """Test multiple queries with browser session management"""
    logger = setup_logging()
    logger.info("=== Testing WITH browser session management ===")
    
    queries = ["laptop", "smartphone", "headphones"]
    scraper = GoogleShoppingScraper(logger=logger, fast_mode=True, keep_browser_open=True)
    
    start_time = time.time()
    
    try:
        for i, query in enumerate(queries, 1):
            logger.info(f"Query {i}/{len(queries)}: {query}")
            query_start = time.time()
            
            items = scraper.get_shopping_data_for_query(query, headless=True)
            
            query_time = time.time() - query_start
            logger.info(f"Query '{query}' completed in {query_time:.2f} seconds, found {len(items)} items")
    
    finally:
        # Clean up browser session
        scraper.close_browser()
    
    total_time = time.time() - start_time
    logger.info(f"Total time WITH session management: {total_time:.2f} seconds")
    
    return total_time


def main():
    """Main function to run performance comparison"""
    print("Google Shopping Scraper - Browser Session Management Performance Test")
    print("=" * 70)
    
    # Test without session management
    time_without = test_multiple_queries_without_session_management()
    
    print("\n" + "=" * 70)
    
    # Test with session management
    time_with = test_multiple_queries_with_session_management()
    
    # Calculate improvement
    improvement = ((time_without - time_with) / time_without) * 100
    
    print("\n" + "=" * 70)
    print("PERFORMANCE COMPARISON RESULTS")
    print("=" * 70)
    print(f"Without browser session management: {time_without:.2f} seconds")
    print(f"With browser session management:    {time_with:.2f} seconds")
    print(f"Time saved:                         {time_without - time_with:.2f} seconds")
    print(f"Performance improvement:            {improvement:.1f}%")
    
    if improvement > 0:
        print(f"\n🚀 Browser session management is {improvement:.1f}% faster!")
    else:
        print(f"\n⚠️  Browser session management was {abs(improvement):.1f}% slower (unexpected)")


if __name__ == "__main__":
    main() 