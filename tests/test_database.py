import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Product, PriceHistory, APIUser

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_product(db_session: AsyncSession):
    new_product = Product(
        source="grailed",
        external_id="12345",
        url="http://example.com",
        brand="Amiri",
        model="T-Shirt",
        currency="USD"
    )
    db_session.add(new_product)
    await db_session.commit()
    await db_session.refresh(new_product)

    assert new_product.id is not None
    assert new_product.brand == "Amiri"

@pytest.mark.asyncio
async def test_create_price_history(db_session: AsyncSession):
    new_product = Product(
        source="fashionphile",
        external_id="fp_1",
        url="http://example.com/fp",
        brand="Tiffany",
        model="Earrings"
    )
    db_session.add(new_product)
    await db_session.flush()

    history = PriceHistory(product_id=new_product.id, price=100.0)
    db_session.add(history)
    await db_session.commit()
    await db_session.refresh(history)

    assert history.id is not None
    assert history.price == 100.0
    assert history.product_id == new_product.id

@pytest.mark.asyncio
async def test_create_api_user(db_session: AsyncSession):
    user = APIUser(api_key="secret123")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.request_count == 0
