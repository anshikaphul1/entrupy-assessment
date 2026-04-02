import pytest
from src.fetchers.base import AsyncFetcher, FetchError
from src.fetchers.parsers import parse_product
import json

@pytest.mark.asyncio
async def test_fetcher_success(tmp_path):
    # Setup dummy JSON file
    dummy_data = {"product_id": "123", "price": 100.0}
    dummy_file = tmp_path / "dummy.json"
    dummy_file.write_text(json.dumps(dummy_data))
    
    # Actually just monkey patching random.random to return 1.0 (no fail)
    import random
    original_random = random.random
    random.random = lambda: 1.0
    
    fetcher = AsyncFetcher(str(dummy_file))
    
    try:
        data = await fetcher.fetch()
        assert data["price"] == 100.0
    finally:
        random.random = original_random

@pytest.mark.asyncio
async def test_fetcher_retry(tmp_path):
    dummy_data = {"product_id": "123", "price": 100.0}
    dummy_file = tmp_path / "dummy.json"
    dummy_file.write_text(json.dumps(dummy_data))
    
    fetcher = AsyncFetcher(str(dummy_file))
    
    import random
    original_random = random.random
    
    # Make it fail exactly once, then succeed
    call_count = 0
    def mock_random():
        nonlocal call_count
        call_count += 1
        return 0.05 if call_count == 1 else 1.0
        
    random.random = mock_random
    
    try:
        data = await fetcher.fetch()
        assert data["price"] == 100.0
        assert call_count == 2
    finally:
        random.random = original_random

def test_parse_grailed():
    data = {
        "product_id": "g1",
        "product_url": "url",
        "brand": "Amiri",
        "model": "Shirt",
        "price": 200.0
    }
    parsed = parse_product("grailed", data)
    assert parsed["source"] == "grailed"
    assert parsed["currency"] == "USD"
    assert parsed["price"] == 200.0

def test_parse_1stdibs():
    data = {
        "product_id": "d1",
        "product_url": "url",
        "metadata": {"brand": "Chanel", "all_prices": {"USD": 400.0}}
    }
    parsed = parse_product("1stdibs", data)
    assert parsed["source"] == "1stdibs"
    assert parsed["brand"] == "Chanel"
    assert parsed["price"] == 400.0
