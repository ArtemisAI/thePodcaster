import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient # Import AsyncClient

# Ensure PYTHONPATH is set up so 'backend.app.main' can be found
from backend.app.main import app as main_app

@pytest.fixture(scope="session")
def app_instance():
    """
    Provides the FastAPI application instance.
    Scope is session to ensure it's initialized only once.
    """
    return main_app

@pytest.fixture(scope="session")
def client(app_instance): # Sync client for TestClient
    """
    Provides a synchronous TestClient instance for the FastAPI application.
    """
    with TestClient(app_instance) as c:
        yield c

@pytest.fixture(scope="function") # Changed to function scope as per httpx recommendation for AsyncClient state
async def async_client(app_instance): # Async client for httpx.AsyncClient
    """
    Provides an asynchronous AsyncClient instance for the FastAPI application.
    """
    # base_url="http://test" is conventional for testing with httpx against an ASGI app.
    async with AsyncClient(app=app_instance, base_url="http://test") as ac:
        yield ac
