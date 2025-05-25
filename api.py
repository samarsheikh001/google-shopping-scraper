#!/usr/bin/env python3
"""
FastAPI application for Google Shopping scraper.
Returns JSON data instead of saving to file.
"""

import logging
import sys
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from google_shopping_scraper.scraper import GoogleShoppingScraper


# Pydantic models for API responses
class ShoppingItem(BaseModel):
    title: str
    price: Optional[str] = None
    delivery_price: Optional[str] = None
    review: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    saved_image_path: Optional[str] = None


class ShoppingResponse(BaseModel):
    query: str
    scraped_at: str
    total_items: int
    items: List[ShoppingItem]


# FastAPI app
app = FastAPI(
    title="Google Shopping Scraper API",
    description="API for scraping Google Shopping data and returning JSON results",
    version="1.0.0"
)

# Global scraper instance for browser session reuse
_global_scraper = None


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


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Google Shopping Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/scrape": "POST - Scrape Google Shopping for a query",
            "/docs": "GET - API documentation"
        }
    }


@app.get("/scrape", response_model=ShoppingResponse)
async def scrape_google_shopping(
    query: str = Query(..., description="Search query for Google Shopping"),
    headless: bool = Query(True, description="Run browser in headless mode"),
    fast: bool = Query(False, description="Enable fast mode for quicker scraping"),
    keep_browser: bool = Query(False, description="Keep browser open between requests")
):
    """
    Scrape Google Shopping for the given query and return JSON results.
    
    Args:
        query: Search query for Google Shopping
        headless: Whether to run browser in headless mode (default: True)
        fast: Whether to enable fast mode for quicker scraping (default: False)
        keep_browser: Whether to keep browser open between requests (default: False)
    
    Returns:
        JSON response with scraped shopping data
    """
    logger = setup_logging()
    
    logger.info(f"API request - Starting Google Shopping scraper for query: '{query}'")
    logger.info(f"Headless mode: {headless}")
    logger.info(f"Fast mode: {fast}")
    logger.info(f"Keep browser open: {keep_browser}")
    
    try:
        # Use global scraper instance if keep_browser is enabled
        global _global_scraper
        
        if keep_browser:
            if _global_scraper is None:
                logger.info("Creating global scraper instance with browser session management")
                _global_scraper = GoogleShoppingScraper(logger=logger, fast_mode=fast, keep_browser_open=True)
            scraper = _global_scraper
        else:
            # Create new scraper instance for this request
            scraper = GoogleShoppingScraper(logger=logger, fast_mode=fast, keep_browser_open=False)
        
        # Scrape data
        items = scraper.get_shopping_data_for_query(query, headless=headless)
        
        if not items:
            logger.warning("No items found!")
            return ShoppingResponse(
                query=query,
                scraped_at=datetime.now().isoformat(),
                total_items=0,
                items=[]
            )
        
        # Convert to API response format
        items_data = []
        for item in items:
            item_dict = ShoppingItem(
                title=item.title,
                price=item.price,
                delivery_price=item.delivery_price,
                review=item.review,
                url=item.url,
                image_url=item.image_url,
                saved_image_path=item.saved_image_path
            )
            items_data.append(item_dict)
        
        # Create response data
        response_data = ShoppingResponse(
            query=query,
            scraped_at=datetime.now().isoformat(),
            total_items=len(items_data),
            items=items_data
        )
        
        logger.info(f"Successfully scraped {len(items)} items for API response")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Error during scraping: {str(e)}")


@app.post("/cleanup")
async def cleanup_browser():
    """
    Cleanup the global browser session.
    Useful when you're done with scraping and want to free resources.
    """
    global _global_scraper
    
    if _global_scraper:
        _global_scraper.close_browser()
        _global_scraper = None
        return {"message": "Browser session cleaned up successfully"}
    else:
        return {"message": "No active browser session to cleanup"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 