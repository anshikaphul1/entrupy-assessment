from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import Product, PriceHistory
from src.database import get_session
from typing import Dict, Any, Tuple

async def process_product(session: AsyncSession, source: str, product_data: Dict[str, Any]) -> Tuple[Product, bool]:
    """
    Process fetched product data.
    Returns (product, price_changed_flag)
    """
    external_id = str(product_data["external_id"])
    
    stmt = select(Product).where(Product.external_id == external_id)
    result = await session.execute(stmt)
    product = result.scalars().first()
    
    new_price = product_data["price"]
    price_changed = False
    
    if not product:
        # Create new product
        product = Product(
            source=source,
            external_id=external_id,
            url=product_data["url"],
            brand=product_data["brand"],
            model=product_data["model"],
            currency=product_data["currency"],
            metadata_json=product_data["metadata_json"]
        )
        session.add(product)
        await session.flush() # get product.id
        
        # Add initial price history
        if new_price is not None:
            history = PriceHistory(product_id=product.id, price=new_price)
            session.add(history)
        
        price_changed = True # Notifying on new items could be optional, let's say true
    else:
        # Check if price changed
        history_stmt = select(PriceHistory).where(PriceHistory.product_id == product.id).order_by(PriceHistory.scraped_at.desc()).limit(1)
        res = await session.execute(history_stmt)
        last_history = res.scalars().first()
        
        if last_history is None or (new_price is not None and last_history.price != new_price):
            history = PriceHistory(product_id=product.id, price=new_price)
            session.add(history)
            price_changed = True
            
        # Update metadata if needed
        product.metadata_json = product_data["metadata_json"]
        
    await session.commit()
    return product, price_changed
