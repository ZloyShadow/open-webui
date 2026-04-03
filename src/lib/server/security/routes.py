"""
API маршруты для управления политиками безопасности и просмотра алертов.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .models import SecurityPolicy, StopWord, SecurityAlert
from .service import security_service

router = APIRouter(prefix="/api/security", tags=["Security"])


# === Pydantic модели для запросов/ответов ===

class StopWordCreate(BaseModel):
    word: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    check_type: str = Field(default='contains', pattern='^(exact|contains|regex)$')
    apply_to_chat: bool = True
    apply_to_api: bool = True
    apply_to_documents: bool = True
    is_active: bool = True


class StopWordResponse(BaseModel):
    id: int
    word: str
    description: Optional[str]
    check_type: str
    apply_to_chat: bool
    apply_to_api: bool
    apply_to_documents: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PolicyCreate(BaseModel):
    name: str = Field(default="Default Policy", max_length=100)
    mode: str = Field(default='audit', pattern='^(audit|block)$')
    notify_email: bool = False
    notify_telegram: bool = False
    notify_slack: bool = False
    email_recipients: List[str] = []
    telegram_chats: List[str] = []
    slack_webhooks: List[str] = []


class PolicyResponse(BaseModel):
    user_id: int
    name: str
    is_active: bool
    mode: str
    notify_email: bool
    notify_telegram: bool
    notify_slack: bool
    email_recipients: List[str]
    telegram_chats: List[str]
    slack_webhooks: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    user_id: int
    policy_id: Optional[int]
    stop_word_id: Optional[int]
    stop_word: Optional[str]
    trigger_content: str
    context_type: str
    context_id: Optional[str]
    action_taken: str
    notifications_sent: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# === Маршруты для политик безопасности ===

@router.get("/policies/{user_id}", response_model=Optional[PolicyResponse])
async def get_user_policy(user_id: int):
    """Получить политику безопасности пользователя."""
    policy = security_service.get_user_policy(user_id)
    if not policy:
        return None
    
    return PolicyResponse(
        user_id=policy.user_id,
        name=policy.name,
        is_active=policy.is_active,
        mode=policy.mode,
        notify_email=policy.notify_email,
        notify_telegram=policy.notify_telegram,
        notify_slack=policy.notify_slack,
        email_recipients=policy.get_email_recipients(),
        telegram_chats=policy.get_telegram_chats(),
        slack_webhooks=policy.get_slack_webhooks(),
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )


@router.post("/policies/{user_id}", response_model=PolicyResponse)
async def create_or_update_policy(user_id: int, policy_data: PolicyCreate):
    """Создать или обновить политику безопасности для пользователя."""
    # Проверяем существующую политику
    existing_policy = security_service.get_user_policy(user_id)
    
    if existing_policy:
        # Обновляем существующую
        for field, value in policy_data.model_dump().items():
            if hasattr(existing_policy, field):
                setattr(existing_policy, field, value)
        
        # Обрабатываем списки как JSON
        existing_policy.email_recipients = str(policy_data.email_recipients) if policy_data.email_recipients else None
        existing_policy.telegram_chats = str(policy_data.telegram_chats) if policy_data.telegram_chats else None
        existing_policy.slack_webhooks = str(policy_data.slack_webhooks) if policy_data.slack_webhooks else None
        
        existing_policy.updated_at = datetime.now()
        existing_policy.save()
        policy = existing_policy
    else:
        # Создаем новую
        policy = SecurityPolicy.create(
            user_id=user_id,
            name=policy_data.name,
            mode=policy_data.mode,
            notify_email=policy_data.notify_email,
            notify_telegram=policy_data.notify_telegram,
            notify_slack=policy_data.notify_slack,
            email_recipients=str(policy_data.email_recipients) if policy_data.email_recipients else None,
            telegram_chats=str(policy_data.telegram_chats) if policy_data.telegram_chats else None,
            slack_webhooks=str(policy_data.slack_webhooks) if policy_data.slack_webhooks else None
        )
    
    return PolicyResponse(
        user_id=policy.user_id,
        name=policy.name,
        is_active=policy.is_active,
        mode=policy.mode,
        notify_email=policy.notify_email,
        notify_telegram=policy.notify_telegram,
        notify_slack=policy.notify_slack,
        email_recipients=policy.get_email_recipients(),
        telegram_chats=policy.get_telegram_chats(),
        slack_webhooks=policy.get_slack_webhooks(),
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )


# === Маршруты для стоп-слов ===

@router.get("/policies/{user_id}/stop-words", response_model=List[StopWordResponse])
async def get_stop_words(user_id: int, context_type: Optional[str] = None):
    """Получить список стоп-слов для политики пользователя."""
    policy = security_service.get_user_policy(user_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    query = StopWord.select().where(StopWord.policy == policy)
    
    if context_type:
        context_filter = f'apply_to_{context_type}'
        if hasattr(StopWord, context_filter):
            query = query.where(getattr(StopWord, context_filter) == True)
    
    stop_words = list(query.order_by(StopWord.created_at.desc()))
    
    return [StopWordResponse.model_validate(sw) for sw in stop_words]


@router.post("/policies/{user_id}/stop-words", response_model=StopWordResponse)
async def add_stop_word(user_id: int, word_data: StopWordCreate):
    """Добавить стоп-слово к политике пользователя."""
    policy = security_service.get_user_policy(user_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    stop_word = StopWord.create(
        policy=policy,
        word=word_data.word,
        description=word_data.description,
        check_type=word_data.check_type,
        apply_to_chat=word_data.apply_to_chat,
        apply_to_api=word_data.apply_to_api,
        apply_to_documents=word_data.apply_to_documents,
        is_active=word_data.is_active
    )
    
    return StopWordResponse.model_validate(stop_word)


@router.delete("/stop-words/{word_id}")
async def delete_stop_word(word_id: int):
    """Удалить стоп-слово."""
    try:
        stop_word = StopWord.get_by_id(word_id)
        stop_word.delete_instance()
        return {"message": "Stop word deleted"}
    except StopWord.DoesNotExist:
        raise HTTPException(status_code=404, detail="Stop word not found")


# === Маршруты для алертов ===

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    user_id: Optional[int] = None,
    context_type: Optional[str] = None,
    action_taken: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """Получить список алертов безопасности с фильтрацией."""
    query = SecurityAlert.select()
    
    if user_id:
        query = query.where(SecurityAlert.user_id == user_id)
    
    if context_type:
        query = query.where(SecurityAlert.context_type == context_type)
    
    if action_taken:
        query = query.where(SecurityAlert.action_taken == action_taken)
    
    alerts = list(query.order_by(SecurityAlert.created_at.desc()).limit(limit).offset(offset))
    
    result = []
    for alert in alerts:
        stop_word_text = None
        if alert.stop_word:
            stop_word_text = alert.stop_word.word
        
        result.append(AlertResponse(
            id=alert.id,
            user_id=alert.user_id,
            policy_id=alert.policy.id if alert.policy else None,
            stop_word_id=alert.stop_word.id if alert.stop_word else None,
            stop_word=stop_word_text,
            trigger_content=alert.trigger_content,
            context_type=alert.context_type,
            context_id=alert.context_id,
            action_taken=alert.action_taken,
            notifications_sent=alert.notifications_sent.split(',') if alert.notifications_sent else [],
            created_at=alert.created_at
        ))
    
    return result


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int):
    """Получить详细信息 об алерте."""
    try:
        alert = SecurityAlert.get_by_id(alert_id)
        
        stop_word_text = None
        if alert.stop_word:
            stop_word_text = alert.stop_word.word
        
        return AlertResponse(
            id=alert.id,
            user_id=alert.user_id,
            policy_id=alert.policy.id if alert.policy else None,
            stop_word_id=alert.stop_word.id if alert.stop_word else None,
            stop_word=stop_word_text,
            trigger_content=alert.trigger_content,
            context_type=alert.context_type,
            context_id=alert.context_id,
            action_taken=alert.action_taken,
            notifications_sent=alert.notifications_sent.split(',') if alert.notifications_sent else [],
            created_at=alert.created_at
        )
    except SecurityAlert.DoesNotExist:
        raise HTTPException(status_code=404, detail="Alert not found")
