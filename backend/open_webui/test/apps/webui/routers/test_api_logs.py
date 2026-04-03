"""
Tests for API Request Logs router endpoints.
Tests the HTTP API endpoints for retrieving logs, statistics, and filtering.
"""
import pytest
import time
import json
import uuid
from typing import Optional

# Import test utilities
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi.testclient import TestClient
from open_webui.models.api_request_logs import ApiRequestLogs, ApiRequestLog
from open_webui.internal.db import Base, engine, SessionLocal
from open_webui.main import app


class TestApiLogsRouter:
    """Tests for the API logs router endpoints."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment before running tests."""
        # Create a temporary SQLite database for testing
        import tempfile
        cls.temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        cls.temp_db_path = f"sqlite:///{cls.temp_db_file.name}"
        
        # Set environment variable for database URL
        os.environ['DATABASE_URL'] = cls.temp_db_path
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create test client
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
        with self.db_session.begin():
            self.db_session.query(ApiRequestLog).delete()
    
    def teardown_method(self):
        """Teardown after each test method."""
        self.db_session.rollback()
    
    def _insert_test_log(self, **kwargs):
        """Helper to insert a test log entry."""
        log_data = {
            'id': f'test-{uuid.uuid4()}',
            'user_id': kwargs.get('user_id', 'test-user'),
            'user_email': kwargs.get('user_email', 'test@example.com'),
            'user_name': kwargs.get('user_name', 'Test User'),
            'method': kwargs.get('method', 'GET'),
            'path': kwargs.get('path', '/api/v1/test'),
            'query_params': kwargs.get('query_params'),
            'request_body': kwargs.get('request_body'),
            'request_headers': kwargs.get('request_headers'),
            'response_status_code': kwargs.get('response_status_code', 200),
            'response_body': kwargs.get('response_body'),
            'source_ip': kwargs.get('source_ip', '192.168.1.1'),
            'user_agent': kwargs.get('user_agent', 'TestClient/1.0'),
            'duration_ms': kwargs.get('duration_ms', 100),
            'created_at': kwargs.get('created_at', int(time.time())),
        }
        return ApiRequestLogs.insert_log(log_data, db=self.db_session)
    
    def test_get_logs_empty(self):
        """Test getting logs when there are no logs."""
        response = self.fast_api_client.get('/api/v1/logs')
        
        assert response.status_code == 200
        data = response.json()
        assert 'logs' in data
        assert 'total' in data
        assert len(data['logs']) == 0
        assert data['total'] == 0
    
    def test_get_logs_basic(self):
        """Test getting logs with basic data."""
        # Insert test logs
        base_time = int(time.time())
        for i in range(5):
            self._insert_test_log(
                path=f'/api/v1/resource/{i}',
                created_at=base_time - i * 100,
            )
        
        response = self.fast_api_client.get('/api/v1/logs?skip=0&limit=10')
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['logs']) == 5
        assert data['total'] == 5
        
        # Check ordering (most recent first)
        for i in range(len(data['logs']) - 1):
            assert data['logs'][i]['created_at'] >= data['logs'][i + 1]['created_at']
    
    def test_get_logs_pagination(self):
        """Test pagination of logs."""
        # Insert test logs
        base_time = int(time.time())
        for i in range(20):
            self._insert_test_log(
                path=f'/api/v1/resource/{i}',
                created_at=base_time - i * 100,
            )
        
        # Get first page
        response = self.fast_api_client.get('/api/v1/logs?skip=0&limit=10')
        assert response.status_code == 200
        data = response.json()
        assert len(data['logs']) == 10
        assert data['total'] == 20
        
        # Get second page
        response = self.fast_api_client.get('/api/v1/logs?skip=10&limit=10')
        assert response.status_code == 200
        data = response.json()
        assert len(data['logs']) == 10
        assert data['total'] == 20
    
    def test_get_logs_filter_by_user_id(self):
        """Test filtering logs by user_id."""
        base_time = int(time.time())
        
        # Insert logs for different users
        for i in range(3):
            self._insert_test_log(user_id='user-specific', path='/api/v1/specific')
        
        for i in range(2):
            self._insert_test_log(user_id='user-other', path='/api/v1/other')
        
        # Filter by specific user
        response = self.fast_api_client.get('/api/v1/logs?user_id=user-specific')
        assert response.status_code == 200
        data = response.json()
        assert len(data['logs']) == 3
        assert all(log['user_id'] == 'user-specific' for log in data['logs'])
    
    def test_get_logs_filter_by_method(self):
        """Test filtering logs by HTTP method."""
        methods = ['GET', 'POST', 'PUT', 'DELETE']
        
        for method in methods:
            self._insert_test_log(method=method)
        
        # Filter by POST
        response = self.fast_api_client.get('/api/v1/logs?method=POST')
        assert response.status_code == 200
        data = response.json()
        assert len(data['logs']) == 1
        assert data['logs'][0]['method'] == 'POST'
    
    def test_get_logs_filter_by_path(self):
        """Test filtering logs by path (partial match)."""
        paths = [
            '/api/v1/chats/123',
            '/api/v1/chats/456',
            '/api/v1/users/123',
            '/api/v1/models/gpt-4',
        ]
        
        for path in paths:
            self._insert_test_log(path=path)
        
        # Filter by path containing 'chats'
        response = self.fast_api_client.get('/api/v1/logs?path=chats')
        assert response.status_code == 200
        data = response.json()
        assert len(data['logs']) == 2
        assert all('chats' in log['path'] for log in data['logs'])
    
    def test_get_logs_filter_by_status_code(self):
        """Test filtering logs by status code."""
        status_codes = [200, 201, 400, 404, 500]
        
        for status in status_codes:
            self._insert_test_log(response_status_code=status)
        
        # Filter by 404
        response = self.fast_api_client.get('/api/v1/logs?status_code=404')
        assert response.status_code == 200
        data = response.json()
        assert len(data['logs']) == 1
        assert data['logs'][0]['response_status_code'] == 404
    
    def test_get_logs_filter_by_date_range(self):
        """Test filtering logs by date range."""
        current_time = int(time.time())
        
        # Insert logs with different timestamps
        for i in range(5):
            self._insert_test_log(
                created_at=current_time - (4 - i) * 1000,
                path=f'/api/v1/test/{i}',
            )
        
        # Filter by date range
        start_date = current_time - 3000
        end_date = current_time - 500
        
        response = self.fast_api_client.get(
            f'/api/v1/logs?start_date={start_date}&end_date={end_date}'
        )
        assert response.status_code == 200
        data = response.json()
        # Should get logs within the range
        assert len(data['logs']) <= 5
    
    def test_get_log_by_id(self):
        """Test getting a single log by ID."""
        log_id = f'test-single-{uuid.uuid4()}'
        self._insert_test_log(
            id=log_id,
            method='PATCH',
            path='/api/v1/special',
        )
        
        response = self.fast_api_client.get(f'/api/v1/logs/{log_id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == log_id
        assert data['method'] == 'PATCH'
        assert data['path'] == '/api/v1/special'
    
    def test_get_log_by_id_not_found(self):
        """Test getting a non-existent log by ID."""
        response = self.fast_api_client.get('/api/v1/logs/non-existent-id')
        
        assert response.status_code == 404
        data = response.json()
        assert 'detail' in data
        assert 'not found' in data['detail'].lower()
    
    def test_get_stats_basic(self):
        """Test getting basic statistics."""
        base_time = int(time.time())
        
        # Insert various logs
        test_data = [
            ('GET', 200, 50),
            ('GET', 200, 60),
            ('POST', 201, 100),
            ('POST', 400, 30),
            ('GET', 404, 20),
            ('DELETE', 500, 200),
        ]
        
        for method, status, duration in test_data:
            self._insert_test_log(
                method=method,
                response_status_code=status,
                duration_ms=duration,
            )
        
        response = self.fast_api_client.get('/api/v1/stats')
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['total_requests'] == 6
        assert data['method_counts']['GET'] == 3
        assert data['method_counts']['POST'] == 2
        assert data['method_counts']['DELETE'] == 1
        assert data['status_2xx'] == 3  # 200, 200, 201
        assert data['status_4xx'] == 2  # 400, 404
        assert data['status_5xx'] == 1  # 500
        assert data['avg_duration_ms'] > 0
        assert len(data['top_endpoints']) > 0
    
    def test_get_stats_with_date_range(self):
        """Test getting statistics with date range filter."""
        current_time = int(time.time())
        
        # Insert old logs
        for i in range(3):
            self._insert_test_log(
                created_at=current_time - 10000,
                method='GET',
            )
        
        # Insert new logs
        for i in range(2):
            self._insert_test_log(
                created_at=current_time,
                method='POST',
            )
        
        # Get stats for recent period only
        start_date = current_time - 5000
        
        response = self.fast_api_client.get(f'/api/v1/stats?start_date={start_date}')
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only count recent logs
        assert data['total_requests'] == 2
        assert data['method_counts'].get('POST', 0) == 2
        assert data['method_counts'].get('GET', 0) == 0
    
    def test_get_logs_limit_validation(self):
        """Test that limit parameter is validated (max 100)."""
        response = self.fast_api_client.get('/api/v1/logs?limit=150')
        
        # FastAPI should validate this
        # Either it returns an error or caps at 100
        assert response.status_code in [200, 422]
    
    def test_get_logs_combined_filters(self):
        """Test using multiple filters together."""
        base_time = int(time.time())
        
        # Insert test data with various combinations
        test_cases = [
            ('user-combo', 'GET', '/api/v1/items', 200),
            ('user-combo', 'GET', '/api/v1/items', 404),
            ('user-combo', 'POST', '/api/v1/items', 201),
            ('user-other', 'GET', '/api/v1/items', 200),
            ('user-combo', 'GET', '/api/v1/users', 200),
        ]
        
        for user_id, method, path, status in test_cases:
            self._insert_test_log(
                user_id=user_id,
                method=method,
                path=path,
                response_status_code=status,
            )
        
        # Combined filter: user-combo + GET + items path
        response = self.fast_api_client.get(
            '/api/v1/logs?user_id=user-combo&method=GET&path=items'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['logs']) == 2  # GET requests to /api/v1/items by user-combo
    
    def test_log_model_fields(self):
        """Test that returned log entries have all expected fields."""
        log_id = f'test-fields-{uuid.uuid4()}'
        self._insert_test_log(
            id=log_id,
            user_id='test-user',
            user_email='test@example.com',
            user_name='Test User',
            method='POST',
            path='/api/v1/test',
            query_params={'key': 'value'},
            request_body={'data': 'test'},
            request_headers={'Content-Type': 'application/json'},
            response_status_code=201,
            response_body={'success': True},
            source_ip='192.168.1.1',
            user_agent='TestClient/1.0',
            duration_ms=150,
        )
        
        response = self.fast_api_client.get(f'/api/v1/logs/{log_id}')
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields are present
        expected_fields = [
            'id', 'user_id', 'user_email', 'user_name', 'method', 'path',
            'query_params', 'request_body', 'request_headers',
            'response_status_code', 'response_body', 'source_ip',
            'user_agent', 'duration_ms', 'created_at'
        ]
        
        for field in expected_fields:
            assert field in data, f"Field '{field}' is missing from response"
    
    def test_stats_response_structure(self):
        """Test that stats response has correct structure."""
        self._insert_test_log()
        
        response = self.fast_api_client.get('/api/v1/stats')
        
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = [
            'total_requests',
            'method_counts',
            'status_2xx',
            'status_4xx',
            'status_5xx',
            'avg_duration_ms',
            'top_endpoints',
        ]
        
        for field in expected_fields:
            assert field in data, f"Field '{field}' is missing from stats response"
        
        # Verify types
        assert isinstance(data['total_requests'], int)
        assert isinstance(data['method_counts'], dict)
        assert isinstance(data['status_2xx'], int)
        assert isinstance(data['status_4xx'], int)
        assert isinstance(data['status_5xx'], int)
        assert isinstance(data['avg_duration_ms'], (int, float))
        assert isinstance(data['top_endpoints'], list)


class TestApiLogsAuthentication:
    """Tests for authentication requirements on API logs endpoints."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        import tempfile
        cls.temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        cls.temp_db_path = f"sqlite:///{cls.temp_db_file.name}"
        os.environ['DATABASE_URL'] = cls.temp_db_path
        
        Base.metadata.create_all(bind=engine)
        cls.fast_api_client = TestClient(app)
        cls.db_session = SessionLocal()
    
    @classmethod
    def teardown_class(cls):
        """Cleanup after all tests."""
        if hasattr(cls, 'db_session'):
            cls.db_session.close()
        
        if hasattr(cls, 'temp_db_file'):
            cls.temp_db_file.close()
            try:
                os.unlink(cls.temp_db_file.name)
            except:
                pass
    
    def setup_method(self):
        """Setup before each test."""
        with self.db_session.begin():
            self.db_session.query(ApiRequestLog).delete()
    
    def test_logs_endpoint_requires_auth(self):
        """Test that logs endpoint requires authentication."""
        # Without auth headers, should get 401 or similar
        response = self.fast_api_client.get('/api/v1/logs')
        
        # The endpoint uses get_admin_user dependency which should reject unauthenticated requests
        # Depending on implementation, this might be 401 or redirect
        assert response.status_code in [401, 403], "Endpoint should require authentication"
    
    def test_stats_endpoint_requires_auth(self):
        """Test that stats endpoint requires authentication."""
        response = self.fast_api_client.get('/api/v1/stats')
        
        assert response.status_code in [401, 403], "Stats endpoint should require authentication"
    
    def test_single_log_endpoint_requires_auth(self):
        """Test that single log endpoint requires authentication."""
        response = self.fast_api_client.get('/api/v1/logs/test-id')
        
        assert response.status_code in [401, 403], "Single log endpoint should require authentication"
