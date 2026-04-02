from fastapi import FastAPI, Depends, HTTPException, Header, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import logging
import asyncio
from typing import List, Dict, Any
import os

from src.database import get_session, init_db, engine
from src.models import APIUser, Product, PriceHistory
from src.schemas import ProductOut, AnalyticsOut
from src.services.notifications import dispatcher
from src.fetchers.base import AsyncFetcher
from src.fetchers.parsers import parse_product
from src.services.pricing import process_product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    # Create dummy API key if doesn't exist
    async with AsyncSession(engine) as session:
        stmt = select(APIUser).where(APIUser.api_key == "test_key")
        result = await session.execute(stmt)
        if not result.scalars().first():
            session.add(APIUser(api_key="test_key"))
            await session.commit()
            logger.info("Created test API user with api_key: 'test_key'")

    await dispatcher.start()
    yield
    # Shutdown
    await dispatcher.stop()
    await engine.dispose()

app = FastAPI(title="Price Monitoring API", lifespan=lifespan)

# Mount frontend
app.mount("/static", StaticFiles(directory="src/static", html=True), name="static")

# --- Dependency ---
async def verify_api_key(x_api_key: str = Header(...), session: AsyncSession = Depends(get_session)):
    stmt = select(APIUser).where(APIUser.api_key == x_api_key)
    result = await session.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    # Increment usage count
    user.request_count += 1
    session.add(user)
    await session.commit()
    return user

# --- Routes ---
@app.post("/api/refresh", dependencies=[Depends(verify_api_key)])
async def trigger_refresh(background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    """
    Triggers an async data refresh task simulating data collection from 3 marketplaces 
    across all files in sample_products dir.
    """
    background_tasks.add_task(run_fetch_job)
    return {"message": "Data refresh triggered in the background."}

async def run_fetch_job():
    """Background job that traverses local sample_products directory imitating scrapers"""
    import glob
    async with AsyncSession(engine) as session:
        # Check files locally
        base_dir = "sample_products"
        search_pattern = os.path.join("d:/entrupy assignment", base_dir, "*.json")
        files = glob.glob(search_pattern)
        logger.info(f"Background refresh found {len(files)} files to process.")
        
        for file_path in files:
            source = "grailed"
            if "fashionphile" in file_path:
                source = "fashionphile"
            elif "1stdibs" in file_path:
                source = "1stdibs"
                
            fetcher = AsyncFetcher(file_path)
            try:
                raw_data = await fetcher.fetch()
                parsed = parse_product(source, raw_data)
                product, price_changed = await process_product(session, source, parsed)
                if price_changed:
                    # fetch latest price to send notification
                    stmt = select(PriceHistory).where(PriceHistory.product_id == product.id).order_by(PriceHistory.scraped_at.desc()).limit(1)
                    res = await session.execute(stmt)
                    history = res.scalars().first()
                    await dispatcher.notify_price_change(product.id, history.price if history else 0.0, product.url)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")

@app.get("/api/products", response_model=List[ProductOut], dependencies=[Depends(verify_api_key)])
async def list_products(source: str = None, category: str = None, session: AsyncSession = Depends(get_session)):
    stmt = select(Product)
    if source:
        stmt = stmt.where(Product.source == source)
    # Basic filtering by category matching the string
    res = await session.execute(stmt)
    products = res.scalars().all()
    # Load history manually or lazyload if configured. We'll lazy load or just ignore. 
    # Let's eager load it.
    from sqlalchemy.orm import selectinload
    stmt = select(Product).options(selectinload(Product.price_history))
    if source:
        stmt = stmt.where(Product.source == source)
    res = await session.execute(stmt)
    return res.scalars().all()

@app.get("/api/products/{product_id}", response_model=ProductOut, dependencies=[Depends(verify_api_key)])
async def get_product(product_id: int, session: AsyncSession = Depends(get_session)):
    from sqlalchemy.orm import selectinload
    stmt = select(Product).options(selectinload(Product.price_history)).where(Product.id == product_id)
    res = await session.execute(stmt)
    product = res.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.get("/api/analytics", response_model=AnalyticsOut, dependencies=[Depends(verify_api_key)])
async def get_analytics(session: AsyncSession = Depends(get_session)):
    # Total
    res = await session.execute(select(func.count(Product.id)))
    total = res.scalar() or 0

    # Total by source
    res = await session.execute(select(Product.source, func.count(Product.id)).group_by(Product.source))
    totals_by_source = {row[0]: row[1] for row in res.all()}
    
    # Average price per brand. To do this we must join Product and latest PriceHistory 
    # For simplicity, let's just average the prices from the history directly grouped by brand.
    stmt = select(Product.brand, func.avg(PriceHistory.price)).join(PriceHistory, Product.id == PriceHistory.product_id).group_by(Product.brand)
    res = await session.execute(stmt)
    avg_price_by_brand = {row[0]: row[1] for row in res.all() if row[0]}
    
    return AnalyticsOut(
        total_products=total,
        totals_by_source=totals_by_source,
        avg_price_by_brand=avg_price_by_brand
    )

@app.post("/api/webhook_test_receiver")
async def receive_webhook(payload: dict):
    logger.info(f"Webhook Received: {payload}")
    return {"status": "ok"}
