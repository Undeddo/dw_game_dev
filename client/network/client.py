"""
DW Reference: Exploration and combat server communication.
Purpose: Wrap network calls with retry/back-off for robustness.
Dependencies: requests, time.
Ext Hooks: Add authentication, encryption.
Client Only: HTTP client with resilience.
"""

import requests
import time
from typing import Optional, Dict, Any

class NetworkClient:
    def __init__(self, base_url: str, max_retries: int = 3, retry_delay: float = 1.0, backoff_factor: float = 2.0):
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor

    def post_with_retry(self, endpoint: str, data: Dict[str, Any], timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Post with exponential backoff retry."""
        url = f"{self.base_url}{endpoint}"
        delay = self.retry_delay
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=data, timeout=timeout)
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Server error {response.status_code} on attempt {attempt + 1}")
            except requests.exceptions.RequestException as e:
                print(f"Network error on attempt {attempt + 1}: {e}")
            
            if attempt < self.max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= self.backoff_factor
        return None

# Usage: client = NetworkClient(SERVER_URL)
# result = client.post_with_retry("/api/move_path", data)
