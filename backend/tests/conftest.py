import warnings
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

TEST_CSRF_TOKEN = "test-csrf-token-for-testing"


class CSRFClient(AsyncClient):
    """AsyncClient that always includes matching CSRF header+cookie."""

    async def request(self, method, url, **kwargs):
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("X-CSRF-Token", TEST_CSRF_TOKEN)
        kwargs["headers"] = headers
        # Force CSRF cookie on every request to prevent login response from overwriting
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            cookies = kwargs.pop("cookies", {}) or {}
            cookies["csrf_token"] = TEST_CSRF_TOKEN
            kwargs["cookies"] = cookies
        return await super().request(method, url, **kwargs)


@pytest_asyncio.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with CSRFClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
