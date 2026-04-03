from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from open_webui.models.api_request_logs import ApiRequestLogs, ApiRequestLogModel
from open_webui.utils.auth import get_admin_user
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session


router = APIRouter()


####################
# Response Models
####################


class ApiLogStatsResponse(BaseModel):
    total_requests: int
    method_counts: dict
    status_2xx: int
    status_4xx: int
    status_5xx: int
    avg_duration_ms: float
    top_endpoints: list[dict]


class ApiLogListResponse(BaseModel):
    logs: list[ApiRequestLogModel]
    total: int


####################
# Endpoints
####################


@router.get('/logs', response_model=ApiLogListResponse)
async def get_api_logs(
    skip: int = Query(0),
    limit: int = Query(50, le=100),
    user_id: Optional[str] = Query(None, description='Filter by user ID'),
    method: Optional[str] = Query(None, description='Filter by HTTP method'),
    path: Optional[str] = Query(None, description='Filter by URL path'),
    status_code: Optional[int] = Query(None, description='Filter by response status code'),
    start_date: Optional[int] = Query(None, description='Start timestamp (epoch)'),
    end_date: Optional[int] = Query(None, description='End timestamp (epoch)'),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get API request logs with optional filters."""
    logs = ApiRequestLogs.get_logs(
        skip=skip,
        limit=limit,
        user_id=user_id,
        method=method,
        path=path,
        status_code=status_code,
        start_date=start_date,
        end_date=end_date,
        db=db,
    )
    
    # Get total count (without pagination)
    total_logs = ApiRequestLogs.get_logs(
        skip=0,
        limit=10000,  # Get a large number to count
        user_id=user_id,
        method=method,
        path=path,
        status_code=status_code,
        start_date=start_date,
        end_date=end_date,
        db=db,
    )
    
    return ApiLogListResponse(logs=logs, total=len(total_logs))


@router.get('/logs/{log_id}', response_model=ApiRequestLogModel)
async def get_api_log_by_id(
    log_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get a single API request log by ID."""
    log = ApiRequestLogs.get_log_by_id(log_id, db=db)
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail='Log entry not found')
    return log


@router.get('/stats', response_model=ApiLogStatsResponse)
async def get_api_log_stats(
    start_date: Optional[int] = Query(None, description='Start timestamp (epoch)'),
    end_date: Optional[int] = Query(None, description='End timestamp (epoch)'),
    group_id: Optional[str] = Query(None, description='Filter by user group ID'),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get summary statistics for API request logs."""
    stats = ApiRequestLogs.get_stats(
        start_date=start_date,
        end_date=end_date,
        group_id=group_id,
        db=db,
    )
    return ApiLogStatsResponse(**stats)
