"""
Модель политик безопасности и стоп-слов для пользователей.
Управляет режимами аудита и блокировки, а также настройками уведомлений.
"""
from peewee import Model, CharField, BooleanField, TextField, IntegerField, ForeignKeyField, DateTimeField
from datetime import datetime
import json

# Предполагается, что User модель уже существует в другом месте
# from src.lib.server.models.user import User 

class SecurityPolicy(Model):
    """
    Политика безопасности для пользователя.
    Определяет режим работы (аудит/блокировка) и настройки уведомлений.
    """
    user_id = IntegerField(unique=True, index=True, help_text="ID пользователя")
    name = CharField(max_length=100, default="Default Policy")
    
    # Режимы работы
    is_active = BooleanField(default=True, help_text="Активна ли политика")
    mode = CharField(
        max_length=20, 
        choices=[('audit', 'Audit'), ('block', 'Block')],
        default='audit',
        help_text="Режим: audit (только логирование) или block (блокировка запроса)"
    )
    
    # Настройки уведомлений
    notify_email = BooleanField(default=False, help_text="Отправлять уведомления на почту")
    notify_telegram = BooleanField(default=False, help_text="Отправлять уведомления в Telegram")
    notify_slack = BooleanField(default=False, help_text="Отправлять уведомления в Slack")
    
    email_recipients = TextField(null=True, help_text="JSON список email адресов")
    telegram_chats = TextField(null=True, help_text="JSON список ID чатов Telegram")
    slack_webhooks = TextField(null=True, help_text="JSON список webhook URL Slack")
    
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    def get_email_recipients(self):
        if self.email_recipients:
            return json.loads(self.email_recipients)
        return []

    def get_telegram_chats(self):
        if self.telegram_chats:
            return json.loads(self.telegram_chats)
        return []

    def get_slack_webhooks(self):
        if self.slack_webhooks:
            return json.loads(self.slack_webhooks)
        return []

    class Meta:
        table_name = 'security_policies'


class StopWord(Model):
    """
    Стоп-слова и маркеры для фильтрации контента.
    Привязываются к политике безопасности.
    """
    policy = ForeignKeyField(SecurityPolicy, backref='stop_words', on_delete='CASCADE')
    word = CharField(max_length=255, index=True, help_text="Стоп-слово или маркер")
    description = TextField(null=True, help_text="Описание причины добавления")
    
    # Типы проверки
    check_type = CharField(
        max_length=20,
        choices=[
            ('exact', 'Exact Match'),
            ('contains', 'Contains'),
            ('regex', 'Regular Expression')
        ],
        default='contains',
        help_text="Тип проверки слова"
    )
    
    # Где применять
    apply_to_chat = BooleanField(default=True, help_text="Применять к чату")
    apply_to_api = BooleanField(default=True, help_text="Применять к API запросам")
    apply_to_documents = BooleanField(default=True, help_text="Применять к документам")
    
    is_active = BooleanField(default=True, help_text="Активно ли правило")
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'stop_words'
        indexes = (
            (('policy', 'word'), True),
        )


class SecurityAlert(Model):
    """
    Журнал сработавших алертов безопасности.
    """
    user_id = IntegerField(index=True, help_text="ID пользователя, нарушившего политику")
    policy = ForeignKeyField(SecurityPolicy, backref='alerts', on_delete='SET NULL', null=True)
    stop_word = ForeignKeyField(StopWord, backref='alerts', on_delete='SET NULL', null=True)
    
    trigger_content = TextField(help_text="Контент, вызвавший срабатывание")
    context_type = CharField(
        max_length=20,
        choices=[('chat', 'Chat'), ('api', 'API'), ('document', 'Document')],
        help_text="Тип контекста, где произошло нарушение"
    )
    context_id = CharField(max_length=100, null=True, help_text="ID чата, запроса или документа")
    
    action_taken = CharField(
        max_length=20,
        choices=[('logged', 'Logged'), ('blocked', 'Blocked')],
        help_text="Предпринятое действие"
    )
    
    notifications_sent = TextField(null=True, help_text="JSON список отправленных уведомлений")
    
    created_at = DateTimeField(default=datetime.now, index=True)

    class Meta:
        table_name = 'security_alerts'
