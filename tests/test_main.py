import pytest
from httpx import AsyncClient
from src.main import app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base, get_session
import asyncio

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def override_get_session():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # insert dummy user
    from src.models import APIUser
    async with TestingSessionLocal() as session:
        session.add(APIUser(api_key="test_key"))
        await session.commit()
    
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_trigger_refresh():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/refresh", headers={"x-api-key": "test_key"})
    assert response.status_code == 200
    assert response.json() == {"message": "Data refresh triggered in the background."}

@pytest.mark.asyncio
async def test_get_analytics():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/analytics", headers={"x-api-key": "test_key"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_products"] == 0

@pytest.mark.asyncio
async def test_unauthorized():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/analytics", headers={"x-api-key": "wrong_key"})
    assert response.status_code == 401
