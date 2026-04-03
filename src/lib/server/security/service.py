"""
Сервис безопасности для фильтрации контента и управления алертами.
Реализует проверку по стоп-словам, отправку уведомлений и применение политик.
"""
import re
import json
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from peewee import DoesNotExist

from .models import SecurityPolicy, StopWord, SecurityAlert

logger = logging.getLogger(__name__)


class SecurityService:
    """
    Основной сервис для проверки контента на нарушения политик безопасности.
    """
    
    def __init__(self):
        pass
    
    def get_user_policy(self, user_id: int) -> Optional[SecurityPolicy]:
        """Получить политику безопасности для пользователя."""
        try:
            return SecurityPolicy.get(SecurityPolicy.user_id == user_id)
        except DoesNotExist:
            return None
    
    def check_content(
        self, 
        content: str, 
        user_id: int, 
        context_type: str,
        context_id: Optional[str] = None
    ) -> Tuple[bool, List[StopWord]]:
        """
        Проверить контент на наличие нарушений.
        
        :param content: Текст для проверки
        :param user_id: ID пользователя
        :param context_type: Тип контекста ('chat', 'api', 'document')
        :param context_id: ID объекта (чат, запрос, документ)
        :return: (нарушение обнаружено, список сработавших правил)
        """
        policy = self.get_user_policy(user_id)
        if not policy or not policy.is_active:
            return False, []
        
        triggered_words = []
        
        # Получаем активные стоп-слова для этой политики
        stop_words = StopWord.select().where(
            StopWord.policy == policy,
            StopWord.is_active == True
        )
        
        # Фильтруем по типу контекста
        # Контекст 'document' должен соответствовать полю 'apply_to_documents'
        if context_type == 'document':
            context_filter = 'apply_to_documents'
        else:
            context_filter = f'apply_to_{context_type}'
        stop_words = [sw for sw in stop_words if getattr(sw, context_filter, False)]
        
        for stop_word in stop_words:
            if self._match_word(content, stop_word):
                triggered_words.append(stop_word)
        
        return len(triggered_words) > 0, triggered_words
    
    def _match_word(self, content: str, stop_word: StopWord) -> bool:
        """Проверить соответствие слова контенту."""
        word = stop_word.word
        
        if stop_word.check_type == 'exact':
            return content == word
        elif stop_word.check_type == 'contains':
            return word.lower() in content.lower()
        elif stop_word.check_type == 'regex':
            try:
                return bool(re.search(word, content, re.IGNORECASE))
            except re.error:
                logger.error(f"Invalid regex pattern: {word}")
                return False
        
        return False
    
    def handle_violation(
        self,
        user_id: int,
        content: str,
        triggered_words: List[StopWord],
        context_type: str,
        context_id: Optional[str] = None
    ) -> bool:
        """
        Обработать нарушение политики безопасности.
        
        :return: True если запрос должен быть заблокирован, False если разрешен
        """
        policy = self.get_user_policy(user_id)
        if not policy:
            return False
        
        should_block = policy.mode == 'block'
        action_taken = 'blocked' if should_block else 'logged'
        
        # Создаем запись об алерте для каждого сработавшего слова
        notifications_sent = []
        
        for stop_word in triggered_words:
            alert = SecurityAlert.create(
                user_id=user_id,
                policy=policy,
                stop_word=stop_word,
                trigger_content=content[:5000],  # Ограничиваем размер
                context_type=context_type,
                context_id=context_id,
                action_taken=action_taken,
                notifications_sent='[]'
            )
            
            # Отправляем уведомления
            sent_channels = self._send_notifications(
                alert=alert,
                policy=policy,
                stop_word=stop_word,
                content=content
            )
            notifications_sent.extend(sent_channels)
            
            # Обновляем запись с информацией об уведомлениях
            alert.notifications_sent = json.dumps(notifications_sent)
            alert.save()
        
        logger.warning(
            f"Security violation detected for user {user_id}. "
            f"Mode: {policy.mode}, Action: {action_taken}, "
            f"Triggered words: {[sw.word for sw in triggered_words]}"
        )
        
        return should_block
    
    def _send_notifications(
        self,
        alert: SecurityAlert,
        policy: SecurityPolicy,
        stop_word: StopWord,
        content: str
    ) -> List[str]:
        """Отправить уведомления по настроенным каналам."""
        sent_channels = []
        
        # Email уведомления
        if policy.notify_email:
            recipients = policy.get_email_recipients()
            for email in recipients:
                if self._send_email_notification(email, alert, stop_word, content):
                    sent_channels.append(f'email:{email}')
        
        # Telegram уведомления
        if policy.notify_telegram:
            chats = policy.get_telegram_chats()
            for chat_id in chats:
                if self._send_telegram_notification(chat_id, alert, stop_word, content):
                    sent_channels.append(f'telegram:{chat_id}')
        
        # Slack уведомления
        if policy.notify_slack:
            webhooks = policy.get_slack_webhooks()
            for webhook in webhooks:
                if self._send_slack_notification(webhook, alert, stop_word, content):
                    sent_channels.append(f'slack:{webhook}')
        
        return sent_channels
    
    def _send_email_notification(
        self, 
        email: str, 
        alert: SecurityAlert, 
        stop_word: StopWord,
        content: str
    ) -> bool:
        """Отправить email уведомление."""
        # Здесь должна быть реальная логика отправки email
        # Для примера просто логируем
        logger.info(f"Sending email to {email}: Security alert triggered by '{stop_word.word}'")
        return True
    
    def _send_telegram_notification(
        self,
        chat_id: str,
        alert: SecurityAlert,
        stop_word: StopWord,
        content: str
    ) -> bool:
        """Отправить уведомление в Telegram."""
        # Здесь должна быть реальная логика отправки в Telegram
        message = (
            f"🚨 Security Alert\n"
            f"User ID: {alert.user_id}\n"
            f"Trigger: {stop_word.word}\n"
            f"Context: {alert.context_type}\n"
            f"Action: {alert.action_taken}"
        )
        logger.info(f"Sending Telegram to {chat_id}: {message}")
        return True
    
    def _send_slack_notification(
        self,
        webhook: str,
        alert: SecurityAlert,
        stop_word: StopWord,
        content: str
    ) -> bool:
        """Отправить уведомление в Slack."""
        # Здесь должна быть реальная логика отправки в Slack
        payload = {
            "text": "🚨 Security Alert",
            "attachments": [
                {
                    "color": "danger" if alert.action_taken == 'blocked' else "warning",
                    "fields": [
                        {"title": "User ID", "value": str(alert.user_id), "short": True},
                        {"title": "Trigger", "value": stop_word.word, "short": True},
                        {"title": "Context", "value": alert.context_type, "short": True},
                        {"title": "Action", "value": alert.action_taken, "short": True}
                    ]
                }
            ]
        }
        logger.info(f"Sending Slack to {webhook}: {json.dumps(payload)}")
        return True


# Глобальный экземпляр сервиса
security_service = SecurityService()


def check_and_handle_security(
    content: str,
    user_id: int,
    context_type: str,
    context_id: Optional[str] = None
) -> bool:
    """
    Удобная функция для проверки и обработки нарушений.
    
    :return: True если запрос разрешен, False если заблокирован
    """
    has_violation, triggered_words = security_service.check_content(
        content=content,
        user_id=user_id,
        context_type=context_type,
        context_id=context_id
    )
    
    if has_violation:
        should_block = security_service.handle_violation(
            user_id=user_id,
            content=content,
            triggered_words=triggered_words,
            context_type=context_type,
            context_id=context_id
        )
        return not should_block
    
    return True
