"""
Abstract integration test base class for API Request Logs testing.
Provides common setup and teardown functionality for database tests.
"""
import pytest
import os
import tempfile
from typing import Optional, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient


class AbstractIntegrationTest:
    """Base class for integration tests with database support."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment before running tests."""
        # Create a temporary SQLite database for testing
        cls.temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        cls.temp_db_path = f"sqlite:///{cls.temp_db_file.name}"
        
        # Set environment variable for database URL
        os.environ['DATABASE_URL'] = cls.temp_db_path
        
        # Import and initialize the app after setting up the database
        from open_webui.internal.db import engine, Base, SessionLocal
        from open_webui.models.api_request_logs import ApiRequestLog
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create test client
        from open_webui.main import app
        cls.fast_api_client = TestClient(app)
        cls.db_session = SessionLocal()
        
    @classmethod
    def teardown_class(cls):
        """Cleanup after all tests are done."""
        if hasattr(cls, 'db_session'):
            cls.db_session.close()
        
        if hasattr(cls, 'temp_db_file'):
            cls.temp_db_file.close()
            try:
                os.unlink(cls.temp_db_file.name)
            except:
                pass
    
    def setup_method(self):
        """Setup before each test method."""
        # Clear all data before each test
        from open_webui.internal.db import Base, engine
        from open_webui.models.api_request_logs import ApiRequestLog
        
        with self.db_session.begin():
            # Delete all records from api_request_log table
            self.db_session.query(ApiRequestLog).delete()
    
    def teardown_method(self):
        """Teardown after each test method."""
        self.db_session.rollback()
    
    def create_url(self, path: str) -> str:
        """Helper to create full URL paths."""
        return f"/api/v1{path}" if not path.startswith('/api') else path


class AbstractPostgresTest(AbstractIntegrationTest):
    """Base class for tests that would use PostgreSQL (using SQLite for simplicity)."""
    # For now, we use SQLite for testing as it's simpler
    # This can be extended to use actual PostgreSQL if needed
    pass
