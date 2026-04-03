"""
Модуль безопасности для фильтрации контента и управления политиками.

Функциональность:
- Политики безопасности для пользователей (режимы audit/block)
- Стоп-слова с различными типами проверки (exact, contains, regex)
- Фильтрация по контекстам (chat, api, documents)
- Уведомления через Email, Telegram, Slack
- Журналирование нарушений (алерты)

Использование:
    from src.lib.server.security.service import check_and_handle_security
    
    # Проверка контента в чате
    allowed = check_and_handle_security(
        content="Текст сообщения",
        user_id=123,
        context_type='chat',
        context_id='chat_001'
    )
    
    if not allowed:
        # Запрос заблокирован политикой безопасности
        return {"error": "Content blocked by security policy"}

API маршруты:
    GET/POST /api/security/policies/{user_id} - Управление политикой пользователя
    GET/POST /api/security/policies/{user_id}/stop-words - Стоп-слова
    DELETE /api/security/stop-words/{word_id} - Удаление стоп-слова
    GET /api/security/alerts - Список алертов с фильтрацией
    GET /api/security/alerts/{alert_id} - Детали алерта
"""

from .models import SecurityPolicy, StopWord, SecurityAlert
from .service import SecurityService, security_service, check_and_handle_security
from .routes import router

__all__ = [
    'SecurityPolicy',
    'StopWord', 
    'SecurityAlert',
    'SecurityService',
    'security_service',
    'check_and_handle_security',
    'router'
]
