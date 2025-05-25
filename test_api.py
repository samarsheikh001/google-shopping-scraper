#!/usr/bin/env python3
"""
Simple test script to verify the API is working correctly.
"""

import requests
import time
import subprocess
import sys
from threading import Thread


def start_api_server():
    """Start the API server in a subprocess"""
    try:
        subprocess.run([sys.executable, "run_api.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting API server: {e}")


def test_api():
    """Test the API endpoints"""
    base_url = "http://localhost:8000"
    
    # Wait a moment for server to start
    time.sleep(3)
    
    try:
        # Test root endpoint
        print("Testing root endpoint...")
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✓ Root endpoint working")
            print(f"Response: {response.json()}")
        else:
            print(f"✗ Root endpoint failed: {response.status_code}")
        
        # Test docs endpoint
        print("\nTesting docs endpoint...")
        response = requests.get(f"{base_url}/docs")
        if response.status_code == 200:
            print("✓ Docs endpoint working")
        else:
            print(f"✗ Docs endpoint failed: {response.status_code}")
        
        print("\nAPI server is running successfully!")
        print(f"Visit {base_url}/docs for interactive API documentation")
        print(f"Example scrape request: {base_url}/scrape?query=test")
        
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to API server")
    except Exception as e:
        print(f"✗ Error testing API: {e}")


if __name__ == "__main__":
    print("Starting API server test...")
    print("Note: This will start the API server. Press Ctrl+C to stop.")
    
    # Start server in background thread
    server_thread = Thread(target=start_api_server, daemon=True)
    server_thread.start()
    
    # Test the API
    test_api()
    
    print("\nAPI server is running. Press Ctrl+C to stop.") 