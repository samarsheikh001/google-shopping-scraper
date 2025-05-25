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
    headless: bool = Query(True, description="Run browser in headless mode")
):
    """
    Scrape Google Shopping for the given query and return JSON results.
    
    Args:
        query: Search query for Google Shopping
        headless: Whether to run browser in headless mode (default: True)
    
    Returns:
        JSON response with scraped shopping data
    """
    logger = setup_logging()
    
    logger.info(f"API request - Starting Google Shopping scraper for query: '{query}'")
    logger.info(f"Headless mode: {headless}")
    
    try:
        # Initialize scraper
        scraper = GoogleShoppingScraper(logger=logger)
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 