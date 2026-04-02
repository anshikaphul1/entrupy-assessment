from typing import Dict, Any, Optional

def parse_grailed(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": "grailed",
        "external_id": data.get("product_id"),
        "url": data.get("product_url"),
        "brand": data.get("brand"),
        "model": data.get("model"),
        "price": data.get("price"),
        "currency": "USD", # Implicit or look from metadata if available
        "metadata_json": data.get("metadata", {})
    }

def parse_fashionphile(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": "fashionphile",
        "external_id": data.get("product_id"),
        "url": data.get("product_url"),
        "brand": data.get("brand"),
        "model": data.get("model"),
        "price": data.get("price"),
        "currency": data.get("currency", "USD"),
        "metadata_json": data.get("metadata", {})
    }

def parse_1stdibs(data: Dict[str, Any]) -> Dict[str, Any]:
    # 1stdibs sometimes puts price inside metadata.all_prices.USD
    price = data.get("price")
    meta = data.get("metadata", {})
    
    if price is None and "all_prices" in meta:
        price = meta["all_prices"].get("USD")
        
    return {
        "source": "1stdibs",
        "external_id": data.get("product_id"),
        "url": data.get("product_url"),
        "brand": data.get("brand", meta.get("brand")),
        "model": data.get("model"),
        "price": price,
        "currency": "USD",
        "metadata_json": meta
    }

PARSERS = {
    "grailed": parse_grailed,
    "fashionphile": parse_fashionphile,
    "1stdibs": parse_1stdibs
}

def parse_product(source: str, data: Dict[str, Any]) -> Dict[str, Any]:
    parser = PARSERS.get(source)
    if not parser:
        raise ValueError(f"Unknown source: {source}")
    return parser(data)
