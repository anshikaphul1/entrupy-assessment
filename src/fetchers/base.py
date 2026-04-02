import json
import asyncio
import random
import aiofiles
from typing import Dict, Any, List
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

class FetchError(Exception):
    pass

class AsyncFetcher:
    """Simulates an async data fetcher that reads from a local JSON file."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(FetchError),
        reraise=True
    )
    async def fetch(self) -> Dict[str, Any]:
        """
        Simulate a network request to an API endpoint that might randomly fail.
        Retries up to 3 times on FetchError.
        """
        await asyncio.sleep(0.01) # Simulate network latency
        
        # 10% chance to fail to demonstrate retry logic
        if random.random() < 0.10:
            raise FetchError(f"Network error simulated for {self.file_path}")

        try:
            async with aiofiles.open(self.file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                return data
        except Exception as e:
            raise FetchError(f"Failed to read/parse {self.file_path}: {e}")
