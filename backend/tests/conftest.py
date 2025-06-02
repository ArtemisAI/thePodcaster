import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient # Import AsyncClient
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Ensure PYTHONPATH is set up so 'backend.app.main' can be found
from backend.app.main import app as main_app
from app.db.database import Base, get_db # Assuming your get_db and Base are here

# Use an in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} # check_same_thread for SQLite
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables at the start of the test session
# This ensures tables are created once before any tests run.
Base.metadata.create_all(bind=engine)

# Fixture to override the get_db dependency
@pytest.fixture(scope="function")
def db() -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Override get_db dependency
    # original_get_db = main_app.dependency_overrides.get(get_db) # Store original if any
    main_app.dependency_overrides[get_db] = lambda: session

    yield session
    
    # Restore original dependency
    # if original_get_db:
    #     main_app.dependency_overrides[get_db] = original_get_db
    # else:
    #     del main_app.dependency_overrides[get_db]
    main_app.dependency_overrides.pop(get_db, None)


    session.close()
    transaction.rollback() # Ensure test isolation
    connection.close()


# app_instance fixture can remain as is
@pytest.fixture(scope="session")
def app_instance():
    """
    Provides the FastAPI application instance.
    Scope is session to ensure it's initialized only once.
    """
    return main_app

# client fixture can remain as is, it will use the overridden get_db via app_instance
@pytest.fixture(scope="function") # Changed to function to ensure db override is fresh
def client(app_instance, db_session_override): # client now depends on db_session_override
    """
    Provides a synchronous TestClient instance for the FastAPI application.
    Ensures that the db session override is active.
    """
    with TestClient(app_instance) as c:
        yield c

@pytest.fixture(scope="function")
async def async_client(app_instance, db_session_override): # async_client now depends on db_session_override
    """
    Provides an asynchronous AsyncClient instance for the FastAPI application.
    Ensures that the db session override is active.
    """
    async with AsyncClient(app=app_instance, base_url="http://test") as ac:
        yield ac

# Helper fixture to manage get_db override, used by client and async_client fixtures
# This is to ensure the dependency override happens correctly with the db session.
@pytest.fixture(scope="function")
def db_session_override(db: Session): # db fixture is the one providing the session
    """This fixture ensures the get_db dependency is overridden with the test session."""
    # The override is now handled within the 'db' fixture itself.
    # This fixture just ensures 'db' is activated for the client fixtures.
    yield
