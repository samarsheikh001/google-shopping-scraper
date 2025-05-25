#!/usr/bin/env python3
"""
Example client script demonstrating how to use the Google Shopping Scraper API.
"""

import requests
import json
import time


def scrape_google_shopping(query, headless=True, api_url="http://localhost:8000"):
    """
    Scrape Google Shopping using the API.
    
    Args:
        query (str): Search query for Google Shopping
        headless (bool): Whether to run browser in headless mode
        api_url (str): Base URL of the API server
    
    Returns:
        dict: JSON response with scraped data
    """
    try:
        response = requests.get(f"{api_url}/scrape", params={
            "query": query,
            "headless": headless
        })
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API server. Make sure it's running.")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def display_results(data):
    """Display the scraped results in a formatted way."""
    if not data:
        print("No data to display.")
        return
    
    print(f"\n{'='*60}")
    print(f"GOOGLE SHOPPING RESULTS")
    print(f"{'='*60}")
    print(f"Query: {data['query']}")
    print(f"Scraped at: {data['scraped_at']}")
    print(f"Total items found: {data['total_items']}")
    print(f"{'='*60}")
    
    if data['total_items'] == 0:
        print("No items found for this query.")
        return
    
    for i, item in enumerate(data['items'], 1):
        print(f"\n{i}. {item['title']}")
        print(f"   Price: {item['price'] or 'N/A'}")
        if item['delivery_price']:
            print(f"   Delivery: {item['delivery_price']}")
        if item['review']:
            print(f"   Review: {item['review']}")
        if item['url']:
            print(f"   URL: {item['url'][:80]}{'...' if len(item['url']) > 80 else ''}")
        print(f"   {'-'*50}")


def save_to_file(data, filename):
    """Save the results to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Results saved to: {filename}")
    except Exception as e:
        print(f"Error saving to file: {e}")


def main():
    """Main function to demonstrate API usage."""
    print("Google Shopping Scraper API Client")
    print("=" * 40)
    
    # Example queries to try
    example_queries = [
        "cat food",
        "wireless headphones",
        "coffee maker",
        "running shoes"
    ]
    
    print("Example queries you can try:")
    for i, query in enumerate(example_queries, 1):
        print(f"{i}. {query}")
    
    # Get user input
    query = input("\nEnter your search query (or press Enter for 'cat food'): ").strip()
    if not query:
        query = "cat food"
    
    headless_input = input("Run in headless mode? (Y/n): ").strip().lower()
    headless = headless_input != 'n'
    
    print(f"\nScraping Google Shopping for: '{query}'")
    print(f"Headless mode: {headless}")
    print("Please wait...")
    
    # Make API request
    start_time = time.time()
    data = scrape_google_shopping(query, headless)
    end_time = time.time()
    
    if data:
        print(f"\nScraping completed in {end_time - start_time:.2f} seconds")
        
        # Display results
        display_results(data)
        
        # Ask if user wants to save to file
        save_input = input(f"\nSave results to JSON file? (y/N): ").strip().lower()
        if save_input == 'y':
            filename = f"shopping_results_{query.replace(' ', '_')}.json"
            save_to_file(data, filename)
    else:
        print("Failed to scrape data. Please check if the API server is running.")


if __name__ == "__main__":
    main() 