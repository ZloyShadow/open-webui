"""
Автотесты для функциональности безопасности: политики, стоп-слова и алерты.
"""
import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from peewee import SqliteDatabase

# Импортируем модели и сервис
from src.lib.server.security.models import SecurityPolicy, StopWord, SecurityAlert
from src.lib.server.security.service import SecurityService, check_and_handle_security


# === Фикстуры для тестов ===

@pytest.fixture
def test_db():
    """Создать тестовую базу данных в памяти."""
    db = SqliteDatabase(':memory:')
    
    # Инициализируем модели с тестовой БД
    models = [SecurityPolicy, StopWord, SecurityAlert]
    db.bind(models)
    db.create_tables(models)
    
    yield db
    
    db.close()


@pytest.fixture
def security_service(test_db):
    """Создать экземпляр сервиса безопасности."""
    return SecurityService()


@pytest.fixture
def sample_policy(test_db, security_service):
    """Создать тестовую политику безопасности."""
    policy = SecurityPolicy.create(
        user_id=123,
        name="Test Policy",
        mode='audit',
        notify_email=True,
        notify_telegram=False,
        notify_slack=True,
        email_recipients=json.dumps(['admin@test.com', 'security@test.com']),
        telegram_chats=None,
        slack_webhooks=json.dumps(['https://hooks.slack.com/test'])
    )
    return policy


@pytest.fixture
def sample_stop_words(test_db, sample_policy):
    """Создать тестовые стоп-слова."""
    words = [
        StopWord.create(
            policy=sample_policy,
            word="spam",
            description="Spam keyword",
            check_type='contains',
            apply_to_chat=True,
            apply_to_api=True,
            apply_to_documents=False,
            is_active=True
        ),
        StopWord.create(
            policy=sample_policy,
            word="confidential",
            description="Sensitive data marker",
            check_type='exact',
            apply_to_chat=True,
            apply_to_api=True,
            apply_to_documents=True,
            is_active=True
        ),
        StopWord.create(
            policy=sample_policy,
            word=r"\bsecret\b",
            description="Regex pattern for secret",
            check_type='regex',
            apply_to_chat=False,
            apply_to_api=True,
            apply_to_documents=True,
            is_active=True
        )
    ]
    return words


# === Тесты моделей ===

class TestSecurityPolicyModel:
    """Тесты модели SecurityPolicy."""
    
    def test_create_policy(self, test_db):
        """Тест создания политики безопасности."""
        policy = SecurityPolicy.create(
            user_id=456,
            name="New Policy",
            mode='block'
        )
        
        assert policy.user_id == 456
        assert policy.name == "New Policy"
        assert policy.mode == 'block'
        assert policy.is_active == True
        assert policy.notify_email == False
        
    def test_policy_json_fields(self, test_db):
        """Тест JSON полей политики."""
        policy = SecurityPolicy.create(
            user_id=789,
            email_recipients=json.dumps(['test@example.com']),
            telegram_chats=json.dumps(['-123456']),
            slack_webhooks=json.dumps(['https://hook.slack.com'])
        )
        
        assert policy.get_email_recipients() == ['test@example.com']
        assert policy.get_telegram_chats() == ['-123456']
        assert policy.get_slack_webhooks() == ['https://hook.slack.com']
    
    def test_get_user_policy(self, test_db, sample_policy):
        """Тест получения политики пользователя."""
        service = SecurityService()
        retrieved = service.get_user_policy(123)
        
        assert retrieved is not None
        assert retrieved.user_id == 123
        assert retrieved.name == "Test Policy"
    
    def test_get_nonexistent_policy(self, test_db, security_service):
        """Тест получения несуществующей политики."""
        policy = security_service.get_user_policy(999)
        assert policy is None


class TestStopWordModel:
    """Тесты модели StopWord."""
    
    def test_create_stop_word(self, test_db, sample_policy):
        """Тест создания стоп-слова."""
        word = StopWord.create(
            policy=sample_policy,
            word="test_word",
            check_type='contains',
            apply_to_chat=True
        )
        
        assert word.word == "test_word"
        assert word.check_type == 'contains'
        assert word.apply_to_chat == True
        assert word.is_active == True
    
    def test_stop_word_relationships(self, test_db, sample_policy, sample_stop_words):
        """Тест связей стоп-слов с политикой."""
        words = list(sample_policy.stop_words)
        assert len(words) == 3
        
        word_texts = [w.word for w in words]
        assert "spam" in word_texts
        assert "confidential" in word_texts


class TestSecurityAlertModel:
    """Тесты модели SecurityAlert."""
    
    def test_create_alert(self, test_db, sample_policy, sample_stop_words):
        """Тест создания алерта."""
        alert = SecurityAlert.create(
            user_id=123,
            policy=sample_policy,
            stop_word=sample_stop_words[0],
            trigger_content="This contains spam word",
            context_type='chat',
            context_id='chat_001',
            action_taken='logged'
        )
        
        assert alert.user_id == 123
        assert alert.context_type == 'chat'
        assert alert.action_taken == 'logged'
        assert alert.stop_word.word == "spam"


# === Тесты сервиса безопасности ===

class TestSecurityService:
    """Тесты SecurityService."""
    
    def test_check_content_no_violation(self, test_db, security_service, sample_policy):
        """Тест проверки контента без нарушений."""
        has_violation, triggered = security_service.check_content(
            content="Normal message without any issues",
            user_id=123,
            context_type='chat'
        )
        
        assert has_violation == False
        assert len(triggered) == 0
    
    def test_check_content_contains_match(self, test_db, security_service, sample_policy, sample_stop_words):
        """Тест проверки на содержит."""
        has_violation, triggered = security_service.check_content(
            content="This message has spam in it",
            user_id=123,
            context_type='chat'
        )
        
        assert has_violation == True
        assert len(triggered) == 1
        assert triggered[0].word == "spam"
    
    def test_check_content_exact_match(self, test_db, security_service, sample_policy, sample_stop_words):
        """Тест проверки на точное совпадение."""
        # Точное совпадение
        has_violation, triggered = security_service.check_content(
            content="confidential",
            user_id=123,
            context_type='chat'
        )
        assert has_violation == True
        assert triggered[0].word == "confidential"
        
        # Не точное совпадение
        has_violation, triggered = security_service.check_content(
            content="confidential data",
            user_id=123,
            context_type='chat'
        )
        assert has_violation == False
    
    def test_check_content_regex_match(self, test_db, security_service, sample_policy, sample_stop_words):
        """Тест проверки regex паттерна."""
        has_violation, triggered = security_service.check_content(
            content="This is a secret message",
            user_id=123,
            context_type='api'
        )
        
        assert has_violation == True
        assert triggered[0].word == r"\bsecret\b"
    
    def test_check_content_context_filtering(self, test_db, security_service, sample_policy, sample_stop_words):
        """Тест фильтрации по контексту."""
        # Слово "spam" не применяется к документам (apply_to_documents=False)
        has_violation, triggered = security_service.check_content(
            content="spam content",
            user_id=123,
            context_type='document'
        )
        assert has_violation == False
        
        # Слово "confidential" применяется к документам (apply_to_documents=True)
        has_violation, triggered = security_service.check_content(
            content="confidential",
            user_id=123,
            context_type='document'
        )
        assert has_violation == True
        assert triggered[0].word == "confidential"
        
        # Слово "spam" применяется к чату
        has_violation, triggered = security_service.check_content(
            content="spam content",
            user_id=123,
            context_type='chat'
        )
        assert has_violation == True
        assert triggered[0].word == "spam"
    
    def test_check_content_inactive_policy(self, test_db, security_service, sample_policy):
        """Тест проверки с неактивной политикой."""
        sample_policy.is_active = False
        sample_policy.save()
        
        has_violation, triggered = security_service.check_content(
            content="spam message",
            user_id=123,
            context_type='chat'
        )
        
        assert has_violation == False
    
    def test_handle_violation_audit_mode(self, test_db, security_service, sample_policy, sample_stop_words):
        """Тест обработки нарушения в режиме аудита."""
        should_block = security_service.handle_violation(
            user_id=123,
            content="spam content here",
            triggered_words=[sample_stop_words[0]],
            context_type='chat',
            context_id='chat_001'
        )
        
        assert should_block == False
        
        # Проверяем, что алерт создан
        alerts = SecurityAlert.select().where(SecurityAlert.user_id == 123)
        assert alerts.count() == 1
        
        alert = alerts[0]
        assert alert.action_taken == 'logged'
        assert alert.context_type == 'chat'
    
    def test_handle_violation_block_mode(self, test_db, security_service, sample_policy, sample_stop_words):
        """Тест обработки нарушения в режиме блокировки."""
        sample_policy.mode = 'block'
        sample_policy.save()
        
        should_block = security_service.handle_violation(
            user_id=123,
            content="spam content here",
            triggered_words=[sample_stop_words[0]],
            context_type='api',
            context_id='req_001'
        )
        
        assert should_block == True
        
        # Проверяем, что алерт создан
        alerts = SecurityAlert.select().where(SecurityAlert.user_id == 123)
        assert alerts.count() == 1
        
        alert = alerts[0]
        assert alert.action_taken == 'blocked'
    
    @patch('src.lib.server.security.service.SecurityService._send_email_notification')
    @patch('src.lib.server.security.service.SecurityService._send_slack_notification')
    def test_handle_violation_notifications(self, mock_slack, mock_email, 
                                           test_db, security_service, sample_policy, sample_stop_words):
        """Тест отправки уведомлений при нарушении."""
        mock_email.return_value = True
        mock_slack.return_value = True
        
        security_service.handle_violation(
            user_id=123,
            content="spam content",
            triggered_words=[sample_stop_words[0]],
            context_type='chat'
        )
        
        # Проверяем вызов методов отправки
        assert mock_email.called
        assert mock_slack.called
        
        # Проверяем, что уведомления записаны в алерт
        alert = SecurityAlert.select().order_by(SecurityAlert.created_at.desc()).first()
        notifications = json.loads(alert.notifications_sent)
        
        assert any(n.startswith('email:') for n in notifications)
        assert any(n.startswith('slack:') for n in notifications)


# === Тесты вспомогательной функции ===

class TestCheckAndHandleSecurity:
    """Тесты функции check_and_handle_security."""
    
    def test_allowed_content(self, test_db, sample_policy):
        """Тест разрешенного контента."""
        result = check_and_handle_security(
            content="Normal safe content",
            user_id=123,
            context_type='chat'
        )
        assert result == True
    
    def test_blocked_content_in_block_mode(self, test_db, sample_policy, sample_stop_words):
        """Тест заблокированного контента в режиме блокировки."""
        sample_policy.mode = 'block'
        sample_policy.save()
        
        result = check_and_handle_security(
            content="spam message",
            user_id=123,
            context_type='chat'
        )
        
        assert result == False
    
    def test_logged_content_in_audit_mode(self, test_db, sample_policy, sample_stop_words):
        """Тест залогированного контента в режиме аудита."""
        result = check_and_handle_security(
            content="spam message",
            user_id=123,
            context_type='chat'
        )
        
        assert result == True  # В режиме аудита запрос разрешен, но залогирован
        
        # Проверяем, что алерт создан
        alerts = SecurityAlert.select().where(SecurityAlert.user_id == 123)
        assert alerts.count() >= 1


# === Интеграционные тесты ===

class TestIntegration:
    """Интеграционные тесты."""
    
    def test_full_workflow_audit_mode(self, test_db, security_service):
        """Полный тест рабочего процесса в режиме аудита."""
        # 1. Создаем политику
        policy = SecurityPolicy.create(
            user_id=999,
            name="Integration Test Policy",
            mode='audit',
            notify_email=True,
            email_recipients=json.dumps(['test@example.com'])
        )
        
        # 2. Добавляем стоп-слова
        StopWord.create(
            policy=policy,
            word="forbidden",
            check_type='contains',
            apply_to_chat=True,
            apply_to_api=True,
            apply_to_documents=True
        )
        
        # 3. Проверяем контент с нарушением
        has_violation, triggered = security_service.check_content(
            content="This contains forbidden word",
            user_id=999,
            context_type='chat'
        )
        
        assert has_violation == True
        assert len(triggered) == 1
        
        # 4. Обрабатываем нарушение
        should_block = security_service.handle_violation(
            user_id=999,
            content="This contains forbidden word",
            triggered_words=triggered,
            context_type='chat',
            context_id='test_chat'
        )
        
        assert should_block == False
        
        # 5. Проверяем создание алерта
        alerts = SecurityAlert.select().where(SecurityAlert.user_id == 999)
        assert alerts.count() == 1
        
        alert = alerts[0]
        assert alert.action_taken == 'logged'
        assert 'forbidden' in alert.trigger_content
    
    def test_multiple_violations(self, test_db, security_service):
        """Тест множественных нарушений в одном сообщении."""
        policy = SecurityPolicy.create(
            user_id=888,
            mode='block'
        )
        
        StopWord.create(
            policy=policy,
            word="bad1",
            check_type='contains'
        )
        StopWord.create(
            policy=policy,
            word="bad2",
            check_type='contains'
        )
        
        has_violation, triggered = security_service.check_content(
            content="Message with bad1 and bad2 words",
            user_id=888,
            context_type='api'
        )
        
        assert has_violation == True
        assert len(triggered) == 2
        
        should_block = security_service.handle_violation(
            user_id=888,
            content="Message with bad1 and bad2 words",
            triggered_words=triggered,
            context_type='api'
        )
        
        assert should_block == True
        
        # Должно быть создано 2 алерта (по одному на каждое слово)
        alerts = SecurityAlert.select().where(SecurityAlert.user_id == 888)
        assert alerts.count() == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
