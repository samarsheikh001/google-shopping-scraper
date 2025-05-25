#!/usr/bin/env python3
"""
Script to scrape Google Shopping and save results as JSON with images.
"""

import argparse
import json
import logging
import sys
from datetime import datetime

from google_shopping_scraper.scraper import GoogleShoppingScraper


def setup_logging():
    """Setup logging configuration"""
    import os
    
    # Create debug directory if it doesn't exist
    debug_dir = "debug"
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(debug_dir, 'scraper.log'))
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Main function to run the scraper"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape Google Shopping and save results as JSON')
    parser.add_argument('query', nargs='?', default='cat food', help='Search query for Google Shopping')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser in headless mode (default: True)')
    parser.add_argument('--no-headless', action='store_false', dest='headless', help='Run browser with visible window')
    args = parser.parse_args()
    
    logger = setup_logging()
    
    logger.info(f"Starting Google Shopping scraper for query: '{args.query}'")
    logger.info(f"Headless mode: {args.headless}")
    
    try:
        # Initialize scraper
        scraper = GoogleShoppingScraper(logger=logger)
        
        # Scrape data
        items = scraper.get_shopping_data_for_query(args.query, headless=args.headless)
        
        if not items:
            logger.warning("No items found!")
            return
        
        # Convert to JSON-serializable format
        items_data = []
        for item in items:
            item_dict = {
                "title": item.title,
                "price": item.price,
                "delivery_price": item.delivery_price,
                "review": item.review,
                "url": item.url,
                "image_url": item.image_url,
                "saved_image_path": item.saved_image_path
            }
            items_data.append(item_dict)
        
        # Create output data with metadata
        output_data = {
            "query": args.query,
            "scraped_at": datetime.now().isoformat(),
            "total_items": len(items_data),
            "items": items_data
        }
        
        # Save to JSON file
        output_filename = f"shopping_results_{args.query.replace(' ', '_')}.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully scraped {len(items)} items")
        logger.info(f"Results saved to: {output_filename}")
        
        # Print summary
        print(f"\n=== SCRAPING RESULTS ===")
        print(f"Query: {args.query}")
        print(f"Items found: {len(items)}")
        print(f"JSON file: {output_filename}")
        
        # Print all items as preview (limited to top 5)
        print(f"\n=== ALL RESULTS ===")
        for i, item in enumerate(items):
            print(f"\n{i+1}. {item.title}")
            print(f"   Price: {item.price}")
            print(f"   Image URL: {item.image_url[:100] + '...' if item.image_url and len(item.image_url) > 100 else item.image_url or 'N/A'}")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 