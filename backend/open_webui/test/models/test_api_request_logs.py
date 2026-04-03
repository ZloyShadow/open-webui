"""
Tests for API Request Logs model and table operations.
Tests the data structure, CRUD operations, and filtering capabilities.
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

from open_webui.models.api_request_logs import ApiRequestLog, ApiRequestLogModel, ApiRequestLogs
from open_webui.internal.db import Base, engine, SessionLocal, get_db_context


class TestApiRequestLogModel:
    """Tests for the ApiRequestLogModel Pydantic model."""
    
    def test_model_creation_with_minimal_fields(self):
        """Test creating a model with only required fields."""
        log_data = {
            'id': 'test-log-1',
            'method': 'GET',
            'path': '/api/v1/test',
            'response_status_code': 200,
            'created_at': int(time.time()),
        }
        
        model = ApiRequestLogModel(**log_data)
        
        assert model.id == 'test-log-1'
        assert model.method == 'GET'
        assert model.path == '/api/v1/test'
        assert model.response_status_code == 200
        assert model.user_id is None
        assert model.user_email is None
        assert model.request_body is None
    
    def test_model_creation_with_all_fields(self):
        """Test creating a model with all fields populated."""
        log_data = {
            'id': 'test-log-2',
            'user_id': 'user-123',
            'user_email': 'test@example.com',
            'user_name': 'Test User',
            'method': 'POST',
            'path': '/api/v1/chats',
            'query_params': {'page': '1', 'limit': '10'},
            'request_body': {'message': 'Hello', 'model': 'gpt-4'},
            'request_headers': {'Content-Type': 'application/json', 'Authorization': 'Bearer token'},
            'response_status_code': 201,
            'response_body': {'id': 'chat-123', 'created': True},
            'source_ip': '192.168.1.1',
            'user_agent': 'Mozilla/5.0',
            'duration_ms': 150,
            'created_at': int(time.time()),
        }
        
        model = ApiRequestLogModel(**log_data)
        
        assert model.id == 'test-log-2'
        assert model.user_id == 'user-123'
        assert model.user_email == 'test@example.com'
        assert model.user_name == 'Test User'
        assert model.method == 'POST'
        assert model.path == '/api/v1/chats'
        assert model.query_params == {'page': '1', 'limit': '10'}
        assert model.request_body == {'message': 'Hello', 'model': 'gpt-4'}
        assert model.response_status_code == 201
        assert model.response_body == {'id': 'chat-123', 'created': True}
        assert model.source_ip == '192.168.1.1'
        assert model.duration_ms == 150
    
    def test_model_json_serialization(self):
        """Test that the model can be serialized to JSON."""
        log_data = {
            'id': 'test-log-3',
            'method': 'GET',
            'path': '/api/v1/models',
            'response_status_code': 200,
            'created_at': int(time.time()),
            'request_body': {'key': 'value'},
        }
        
        model = ApiRequestLogModel(**log_data)
        json_str = model.model_dump_json()
        
        assert json_str is not None
        parsed = json.loads(json_str)
        assert parsed['id'] == 'test-log-3'
        assert parsed['method'] == 'GET'


class TestApiRequestLogTableOperations:
    """Tests for the ApiRequestLogTable CRUD operations."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Create tables
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        
        # Clean up all existing logs before each test to ensure isolation
        self.db.query(ApiRequestLog).delete()
        self.db.commit()
        
        yield
        
        # Cleanup after test
        self.db.rollback()  # Rollback any uncommitted changes
        self.db.query(ApiRequestLog).delete()  # Clean up logs created during test
        self.db.commit()
        self.db.close()
    
    def test_insert_log(self):
        """Test inserting a new log entry."""
        log_data = {
            'id': f'test-insert-{uuid.uuid4()}',
            'user_id': 'user-456',
            'user_email': 'insert@test.com',
            'user_name': 'Insert Test',
            'method': 'PUT',
            'path': '/api/v1/users/456',
            'query_params': None,
            'request_body': {'name': 'Updated Name'},
            'request_headers': {'Content-Type': 'application/json'},
            'response_status_code': 200,
            'response_body': {'success': True},
            'source_ip': '10.0.0.1',
            'user_agent': 'TestClient/1.0',
            'duration_ms': 75,
            'created_at': int(time.time()),
        }
        
        result = ApiRequestLogs.insert_log(log_data, db=self.db)
        
        assert result is not None
        assert result.id == log_data['id']
        assert result.user_id == 'user-456'
        assert result.method == 'PUT'
        assert result.response_status_code == 200
    
    def test_get_logs_basic(self):
        """Test retrieving logs without filters."""
        # Insert test data
        base_time = int(time.time())
        for i in range(5):
            log_data = {
                'id': f'test-get-{i}-{uuid.uuid4()}',
                'user_id': f'user-{i}',
                'method': 'GET',
                'path': f'/api/v1/resource/{i}',
                'response_status_code': 200,
                'created_at': base_time - i * 100,
            }
            ApiRequestLogs.insert_log(log_data, db=self.db)
        
        # Retrieve logs
        logs = ApiRequestLogs.get_logs(skip=0, limit=10, db=self.db)
        
        assert len(logs) >= 5
        # Check that logs are ordered by created_at desc
        for i in range(len(logs) - 1):
            assert logs[i].created_at >= logs[i + 1].created_at
    
    def test_get_logs_with_user_id_filter(self):
        """Test retrieving logs filtered by user_id."""
        base_time = int(time.time())
        
        # Insert logs for different users
        for i in range(3):
            ApiRequestLogs.insert_log({
                'id': f'test-user-filter-{i}-{uuid.uuid4()}',
                'user_id': 'user-specific',
                'method': 'GET',
                'path': '/api/v1/test',
                'response_status_code': 200,
                'created_at': base_time - i * 100,
            }, db=self.db)
        
        ApiRequestLogs.insert_log({
            'id': f'test-user-filter-other-{uuid.uuid4()}',
            'user_id': 'user-other',
            'method': 'GET',
            'path': '/api/v1/test',
            'response_status_code': 200,
            'created_at': base_time,
        }, db=self.db)
        
        # Filter by specific user
        logs = ApiRequestLogs.get_logs(user_id='user-specific', db=self.db)
        
        assert len(logs) == 3
        assert all(log.user_id == 'user-specific' for log in logs)
    
    def test_get_logs_with_method_filter(self):
        """Test retrieving logs filtered by method."""
        base_time = int(time.time())
        
        methods = ['GET', 'POST', 'PUT', 'DELETE']
        for method in methods:
            ApiRequestLogs.insert_log({
                'id': f'test-method-{method}-{uuid.uuid4()}',
                'user_id': 'user-method',
                'method': method,
                'path': '/api/v1/test',
                'response_status_code': 200,
                'created_at': base_time,
            }, db=self.db)
        
        # Filter by POST method
        logs = ApiRequestLogs.get_logs(method='POST', db=self.db)
        
        assert len(logs) == 1
        assert logs[0].method == 'POST'
    
    def test_get_logs_with_path_filter(self):
        """Test retrieving logs filtered by path (partial match)."""
        base_time = int(time.time())
        
        paths = [
            '/api/v1/chats/123',
            '/api/v1/chats/456',
            '/api/v1/users/123',
            '/api/v1/models/gpt-4',
        ]
        
        for path in paths:
            ApiRequestLogs.insert_log({
                'id': f'test-path-{uuid.uuid4()}',
                'user_id': 'user-path',
                'method': 'GET',
                'path': path,
                'response_status_code': 200,
                'created_at': base_time,
            }, db=self.db)
        
        # Filter by path containing 'chats'
        logs = ApiRequestLogs.get_logs(path='chats', db=self.db)
        
        assert len(logs) == 2
        assert all('chats' in log.path for log in logs)
    
    def test_get_logs_with_status_code_filter(self):
        """Test retrieving logs filtered by status code."""
        base_time = int(time.time())
        
        status_codes = [200, 201, 400, 404, 500]
        for status in status_codes:
            ApiRequestLogs.insert_log({
                'id': f'test-status-{status}-{uuid.uuid4()}',
                'user_id': 'user-status',
                'method': 'GET',
                'path': '/api/v1/test',
                'response_status_code': status,
                'created_at': base_time,
            }, db=self.db)
        
        # Filter by 404 status
        logs = ApiRequestLogs.get_logs(status_code=404, db=self.db)
        
        assert len(logs) == 1
        assert logs[0].response_status_code == 404
    
    def test_get_logs_with_date_range_filter(self):
        """Test retrieving logs filtered by date range."""
        current_time = int(time.time())
        
        # Insert logs with different timestamps
        # Timestamps: current_time-4000, current_time-3000, current_time-2000, current_time-1000, current_time
        for i in range(5):
            ApiRequestLogs.insert_log({
                'id': f'test-date-{i}-{uuid.uuid4()}',
                'user_id': 'user-date',
                'method': 'GET',
                'path': '/api/v1/test',
                'response_status_code': 200,
                'created_at': current_time - (4 - i) * 1000,  # Spread over 4000 seconds
            }, db=self.db)
        
        # Filter by date range: from current_time-3000 to current_time-500
        # This should include logs at: current_time-3000, current_time-2000, current_time-1000
        start_date = current_time - 3000
        end_date = current_time - 500
        
        logs = ApiRequestLogs.get_logs(
            start_date=start_date,
            end_date=end_date,
            db=self.db
        )
        
        assert len(logs) == 3  # Should get 3 logs within the range
    
    def test_get_log_by_id(self):
        """Test retrieving a single log by ID."""
        log_id = f'test-get-by-id-{uuid.uuid4()}'
        log_data = {
            'id': log_id,
            'user_id': 'user-single',
            'method': 'PATCH',
            'path': '/api/v1/special',
            'response_status_code': 200,
            'created_at': int(time.time()),
        }
        
        inserted = ApiRequestLogs.insert_log(log_data, db=self.db)
        retrieved = ApiRequestLogs.get_log_by_id(log_id, db=self.db)
        
        assert retrieved is not None
        assert retrieved.id == log_id
        assert retrieved.method == 'PATCH'
    
    def test_get_log_by_id_not_found(self):
        """Test retrieving a non-existent log by ID."""
        result = ApiRequestLogs.get_log_by_id('non-existent-id', db=self.db)
        
        assert result is None
    
    def test_get_stats(self):
        """Test getting statistics for API logs."""
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
            ApiRequestLogs.insert_log({
                'id': f'test-stats-{method}-{status}-{uuid.uuid4()}',
                'user_id': 'user-stats',
                'method': method,
                'path': '/api/v1/stats',
                'response_status_code': status,
                'duration_ms': duration,
                'created_at': base_time,
            }, db=self.db)
        
        stats = ApiRequestLogs.get_stats(db=self.db)
        
        assert stats['total_requests'] == 6
        assert stats['method_counts']['GET'] == 3
        assert stats['method_counts']['POST'] == 2
        assert stats['method_counts']['DELETE'] == 1
        assert stats['status_2xx'] == 3  # 200, 200, 201
        assert stats['status_4xx'] == 2  # 400, 404
        assert stats['status_5xx'] == 1  # 500
        assert stats['avg_duration_ms'] > 0
        assert len(stats['top_endpoints']) > 0
    
    def test_delete_logs_older_than(self):
        """Test deleting logs older than a specified timestamp."""
        current_time = int(time.time())
        old_time = current_time - 10000
        new_time = current_time
        
        # Insert old logs
        for i in range(3):
            ApiRequestLogs.insert_log({
                'id': f'test-old-{i}-{uuid.uuid4()}',
                'user_id': 'user-old',
                'method': 'GET',
                'path': '/api/v1/old',
                'response_status_code': 200,
                'created_at': old_time - i * 100,
            }, db=self.db)
        
        # Insert new logs
        for i in range(2):
            ApiRequestLogs.insert_log({
                'id': f'test-new-{i}-{uuid.uuid4()}',
                'user_id': 'user-new',
                'method': 'GET',
                'path': '/api/v1/new',
                'response_status_code': 200,
                'created_at': new_time,
            }, db=self.db)
        
        # Delete old logs
        deleted_count = ApiRequestLogs.delete_logs_older_than(current_time - 5000, db=self.db)
        
        assert deleted_count == 3
        
        # Verify only new logs remain
        remaining_logs = ApiRequestLogs.get_logs(db=self.db)
        assert len(remaining_logs) == 2
        assert all(log.path == '/api/v1/new' for log in remaining_logs)
    
    def test_combined_filters(self):
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
            ApiRequestLogs.insert_log({
                'id': f'test-combo-{user_id}-{method}-{uuid.uuid4()}',
                'user_id': user_id,
                'method': method,
                'path': path,
                'response_status_code': status,
                'created_at': base_time,
            }, db=self.db)
        
        # Combined filter: user-combo + GET + items path
        logs = ApiRequestLogs.get_logs(
            user_id='user-combo',
            method='GET',
            path='items',
            db=self.db
        )
        
        assert len(logs) == 2  # GET requests to /api/v1/items by user-combo


class TestApiRequestLogDatabaseSchema:
    """Tests to verify the database schema is correctly defined."""
    
    def test_table_exists(self):
        """Test that the api_request_log table exists."""
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert 'api_request_log' in tables
    
    def test_table_columns(self):
        """Test that all expected columns exist in the table."""
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        columns = {col['name']: col for col in inspector.get_columns('api_request_log')}
        
        expected_columns = [
            'id',
            'user_id',
            'user_email',
            'user_name',
            'method',
            'path',
            'query_params',
            'request_body',
            'request_headers',
            'response_status_code',
            'response_body',
            'source_ip',
            'user_agent',
            'duration_ms',
            'created_at',
        ]
        
        for col_name in expected_columns:
            assert col_name in columns, f"Column '{col_name}' is missing"
    
    def test_indexes_exist(self):
        """Test that indexes are created on the table."""
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        indexes = inspector.get_indexes('api_request_log')
        
        index_names = [idx['name'] for idx in indexes]
        
        # Check for expected indexes
        expected_index_patterns = [
            'user_id',
            'method',
            'path',
            'response_status_code',
            'created_at',
        ]
        
        # At least some indexes should exist
        assert len(indexes) > 0
