# Система безопасности: Политики, Стоп-слова и Алерты

## Обзор

Реализована комплексная система фильтрации контента и управления политиками безопасности для пользователей системы. Функциональность включает:

- **Политики безопасности** - индивидуальные настройки для каждого пользователя
- **Стоп-слова** - гибкая система фильтрации с различными типами проверок
- **Алерты** - журналирование нарушений с уведомлениями
- **Уведомления** - поддержка Email, Telegram, Slack

## Структура проекта

```
src/lib/server/security/
├── __init__.py          # Экспорт модуля
├── models.py            # Модели базы данных (SecurityPolicy, StopWord, SecurityAlert)
├── service.py           # Бизнес-логика и сервис проверки контента
└── routes.py            # API маршруты для управления

src/lib/components/admin/security/
└── SecurityPolicies.svelte  # UI компонент админ-панели

tests/unit/security/
└── test_security.py     # Автотесты (21 тест)
```

## Модели данных

### SecurityPolicy
Политика безопасности пользователя:
- `user_id` - ID пользователя (уникальный)
- `mode` - режим работы: `audit` (только логирование) или `block` (блокировка)
- `notify_email/telegram/slack` - включение каналов уведомлений
- `email_recipients/telegram_chats/slack_webhooks` - списки получателей (JSON)

### StopWord
Стоп-слова для фильтрации:
- `word` - слово или паттерн
- `check_type` - тип проверки: `exact`, `contains`, `regex`
- `apply_to_chat/api/documents` - применение к контекстам
- `is_active` - активность правила

### SecurityAlert
Журнал нарушений:
- `user_id` - нарушитель
- `trigger_content` - контент, вызвавший нарушение
- `context_type` - контекст: `chat`, `api`, `document`
- `action_taken` - действие: `logged`, `blocked`
- `notifications_sent` - отправленные уведомления (JSON)

## API Endpoints

### Политики безопасности
```
GET  /api/security/policies/{user_id}           # Получить политику
POST /api/security/policies/{user_id}           # Создать/обновить политику
```

### Стоп-слова
```
GET  /api/security/policies/{user_id}/stop-words         # Список стоп-слов
POST /api/security/policies/{user_id}/stop-words         # Добавить стоп-слово
DELETE /api/security/stop-words/{word_id}                # Удалить стоп-слово
```

### Алерты
```
GET /api/security/alerts                  # Список алертов (с фильтрацией)
GET /api/security/alerts/{alert_id}       # Детали алерта
```

## Использование в коде

```python
from src.lib.server.security import check_and_handle_security

# Проверка сообщения в чате
allowed = check_and_handle_security(
    content="Текст сообщения пользователя",
    user_id=123,
    context_type='chat',
    context_id='chat_001'
)

if not allowed:
    return {"error": "Content blocked by security policy"}

# Проверка API запроса
allowed = check_and_handle_security(
    content=request_body,
    user_id=456,
    context_type='api',
    context_id=request_id
)

# Проверка документа
allowed = check_and_handle_security(
    content=document_text,
    user_id=789,
    context_type='document',
    context_id=document_id
)
```

## Режимы работы

### Audit (Аудит)
- Нарушения логируются в базу данных
- Создаются алерты
- Отправляются уведомления администраторам
- **Запрос НЕ блокируется**

### Block (Блокировка)
- Нарушения логируются в базу данных
- Создаются алерты
- Отправляются уведомления администраторам
- **Запрос БЛОКИРУЕТСЯ**

## Типы проверки стоп-слов

1. **Contains** (по умолчанию) - проверка на содержание подстроки (регистронезависимая)
2. **Exact** - точное совпадение всего текста
3. **Regex** - проверка по регулярному выражению

## Контексты применения

Стоп-слова можно применять выборочно к:
- Чатам (`apply_to_chat`)
- API запросам (`apply_to_api`)
- Документам (`apply_to_documents`)

## UI Компонент

Компонент `SecurityPolicies.svelte` предоставляет интерфейс администратора для:
- Просмотра и редактирования политик пользователей
- Управления стоп-словами (добавление, удаление, настройка)
- Просмотра истории алертов с фильтрацией
- Настройки каналов уведомлений

## Тестирование

Запуск автотестов:
```bash
pytest tests/unit/security/test_security.py -v
```

Покрытие тестами:
- ✅ Создание и получение политик
- ✅ JSON поля политик
- ✅ Создание стоп-слов
- ✅ Связи между моделями
- ✅ Создание алертов
- ✅ Проверка контента (все типы匹配)
- ✅ Фильтрация по контекстам
- ✅ Обработка нарушений (audit/block режимы)
- ✅ Отправка уведомлений
- ✅ Интеграционные тесты полного цикла

**Результат: 21 тест пройден успешно**

## Пример настройки политики через API

```bash
# Создать политику для пользователя 123
curl -X POST http://localhost:8000/api/security/policies/123 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Strict Policy",
    "mode": "block",
    "notify_email": true,
    "notify_telegram": true,
    "email_recipients": ["admin@example.com"],
    "telegram_chats": ["-1001234567890"]
  }'

# Добавить стоп-слово
curl -X POST http://localhost:8000/api/security/policies/123/stop-words \
  -H "Content-Type: application/json" \
  -d '{
    "word": "confidential",
    "description": "Sensitive data marker",
    "check_type": "contains",
    "apply_to_chat": true,
    "apply_to_api": true,
    "apply_to_documents": true
  }'
```

## Миграции базы данных

Для применения новых таблиц выполните миграции:
```python
from src.lib.server.security.models import SecurityPolicy, StopWord, SecurityAlert

# Создать таблицы (если используются напрямую)
db.create_tables([SecurityPolicy, StopWord, SecurityAlert])
```

Или используйте систему миграций проекта (peewee-migrate).
