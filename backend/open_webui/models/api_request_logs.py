import json
import time
from typing import Optional, Any

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, get_db_context

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Column,
    Text,
    JSON,
    Index,
    func,
)


####################
# API Request Log DB Schema
####################


class ApiRequestLog(Base):
    __tablename__ = 'api_request_log'

    # Identity
    id = Column(Text, primary_key=True)
    
    # User info
    user_id = Column(Text, index=True, nullable=True)
    user_email = Column(Text, index=True, nullable=True)
    user_name = Column(Text, nullable=True)
    
    # Request info
    method = Column(Text, index=True)  # GET, POST, PUT, DELETE, etc.
    path = Column(Text, index=True)  # URL path
    query_params = Column(JSON, nullable=True)  # Query parameters
    
    # Request details
    request_body = Column(JSON, nullable=True)
    request_headers = Column(JSON, nullable=True)
    
    # Response info
    response_status_code = Column(BigInteger, index=True)
    response_body = Column(JSON, nullable=True)
    
    # Network info
    source_ip = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timing
    duration_ms = Column(BigInteger, nullable=True)  # Request duration in milliseconds
    
    # Timestamps
    created_at = Column(BigInteger, index=True)  # timestamp in epoch seconds
    
    __table_args__ = (
        Index('api_request_log_user_created_idx', 'user_id', 'created_at'),
        Index('api_request_log_path_created_idx', 'path', 'created_at'),
        Index('api_request_log_method_created_idx', 'method', 'created_at'),
    )


####################
# Pydantic Models
####################


class ApiRequestLogModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    method: str
    path: str
    query_params: Optional[dict] = None
    request_body: Optional[Any] = None
    request_headers: Optional[dict] = None
    response_status_code: Optional[int] = None
    response_body: Optional[Any] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: int


####################
# Table Operations
####################


class ApiRequestLogTable:
    def insert_log(
        self,
        log_data: dict,
        db: Optional[Session] = None,
    ) -> Optional[ApiRequestLogModel]:
        """Insert a new API request log entry."""
        with get_db_context(db) as db:
            log_entry = ApiRequestLog(**log_data)
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return ApiRequestLogModel.model_validate(log_entry)
    
    def get_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        user_id: Optional[str] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        status_code: Optional[int] = None,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> list[ApiRequestLogModel]:
        """Get API request logs with optional filters."""
        with get_db_context(db) as db:
            query = db.query(ApiRequestLog)
            
            if user_id:
                query = query.filter(ApiRequestLog.user_id == user_id)
            if method:
                query = query.filter(ApiRequestLog.method == method)
            if path:
                query = query.filter(ApiRequestLog.path.contains(path))
            if status_code:
                query = query.filter(ApiRequestLog.response_status_code == status_code)
            if start_date:
                query = query.filter(ApiRequestLog.created_at >= start_date)
            if end_date:
                query = query.filter(ApiRequestLog.created_at <= end_date)
            
            logs = (
                query
                .order_by(ApiRequestLog.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [ApiRequestLogModel.model_validate(log) for log in logs]
    
    def get_log_by_id(self, log_id: str, db: Optional[Session] = None) -> Optional[ApiRequestLogModel]:
        """Get a single log entry by ID."""
        with get_db_context(db) as db:
            log = db.get(ApiRequestLog, log_id)
            return ApiRequestLogModel.model_validate(log) if log else None
    
    def get_stats(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict:
        """Get summary statistics for API logs."""
        with get_db_context(db) as db:
            from open_webui.models.groups import GroupMember
            
            query = db.query(ApiRequestLog)
            
            if start_date:
                query = query.filter(ApiRequestLog.created_at >= start_date)
            if end_date:
                query = query.filter(ApiRequestLog.created_at <= end_date)
            if group_id:
                group_users = db.query(GroupMember.user_id).filter(GroupMember.group_id == group_id).subquery()
                query = query.filter(ApiRequestLog.user_id.in_(group_users))
            
            total_requests = query.count()
            
            # Count by method
            method_counts = (
                db.query(ApiRequestLog.method, func.count(ApiRequestLog.id))
                .filter(
                    ApiRequestLog.created_at >= start_date if start_date else True,
                    ApiRequestLog.created_at <= end_date if end_date else True,
                )
                .group_by(ApiRequestLog.method)
                .all()
            )
            
            # Count by status code category
            status_2xx = query.filter(
                ApiRequestLog.response_status_code >= 200,
                ApiRequestLog.response_status_code < 300,
            ).count() if query.filter(
                ApiRequestLog.response_status_code >= 200,
                ApiRequestLog.response_status_code < 300,
            ).count() else 0
            
            status_4xx = query.filter(
                ApiRequestLog.response_status_code >= 400,
                ApiRequestLog.response_status_code < 500,
            ).count()
            
            status_5xx = query.filter(
                ApiRequestLog.response_status_code >= 500,
                ApiRequestLog.response_status_code < 600,
            ).count()
            
            # Average response time
            avg_duration = (
                db.query(func.avg(ApiRequestLog.duration_ms))
                .filter(
                    ApiRequestLog.duration_ms.isnot(None),
                    ApiRequestLog.created_at >= start_date if start_date else True,
                    ApiRequestLog.created_at <= end_date if end_date else True,
                )
                .scalar()
            ) or 0
            
            # Top endpoints by request count
            top_endpoints = (
                db.query(ApiRequestLog.path, func.count(ApiRequestLog.id).label('count'))
                .filter(
                    ApiRequestLog.created_at >= start_date if start_date else True,
                    ApiRequestLog.created_at <= end_date if end_date else True,
                )
                .group_by(ApiRequestLog.path)
                .order_by(func.count(ApiRequestLog.id).desc())
                .limit(10)
                .all()
            )
            
            return {
                'total_requests': total_requests,
                'method_counts': dict(method_counts),
                'status_2xx': status_2xx,
                'status_4xx': status_4xx,
                'status_5xx': status_5xx,
                'avg_duration_ms': float(avg_duration),
                'top_endpoints': [{'path': path, 'count': count} for path, count in top_endpoints],
            }
    
    def delete_logs_older_than(self, timestamp: int, db: Optional[Session] = None) -> int:
        """Delete logs older than specified timestamp. Returns count of deleted logs."""
        with get_db_context(db) as db:
            deleted = (
                db.query(ApiRequestLog)
                .filter(ApiRequestLog.created_at < timestamp)
                .delete(synchronize_session=False)
            )
            db.commit()
            return deleted


ApiRequestLogs = ApiRequestLogTable()
