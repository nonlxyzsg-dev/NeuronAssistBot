# NeuronAssistBot

Telegram-бот-модератор для discussion group комментариев канала «Банка с нейронами».

## Возможности

- Верификация новых участников через кнопку.
- Профанити-фильтр с загрузкой словаря из файла.
- Голосование за спам по упоминанию бота в ответе.
- Экспорт списка верифицированных пользователей.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Переменные окружения

Создайте `.env`:

```dotenv
BOT_TOKEN=123456:ABCDEF
DISCUSSION_CHAT_ID=-1001234567890
DATABASE_URL=postgresql://user:password@localhost:5432/moderation
SPAM_THRESHOLD=5
VOTE_TTL_SECONDS=600
PROFANITY_WORDS_PATH=profanity_words.txt
```

## Запуск

```bash
python main.py
```

## Права бота

- `Delete messages` (удаление сообщений)
- `Restrict members` (ограничение участников)
- `Pin messages` (опционально)
- `Read messages`

Отключите **Privacy Mode** в BotFather, чтобы бот видел сообщения в группе.

## Тесты

```bash
pytest
```
