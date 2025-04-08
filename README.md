# Content Generator Bot

Telegram bot with Django admin panel for automated content generation and management.

## Features

- 🤖 Telegram bot for content generation and management
- 👩‍💼 Django admin panel for content management
- 🎯 Topic-based content generation using OpenAI
- 📝 Post editing and scheduling
- 🌐 Multi-language support (ru/en)
- 🔄 Automated posting to Telegram channel
- 👥 Multi-user access with role-based permissions

## Tech Stack

- Python 3.10+
- Django 4.2
- PostgreSQL
- OpenAI API
- Telegram Bot API
- Celery for task scheduling
- Redis for caching
- Docker & Docker Compose

## Setup with Docker

1. Clone the repository:
```bash
git clone https://github.com/yourusername/content-generator-bot.git
cd content-generator-bot
```

2. Create .env file:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Build and start containers:
```bash
docker-compose up --build
```

4. Create superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

5. Access the application:
- Django Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/

## Manual Setup (without Docker)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/content-generator-bot.git
cd content-generator-bot
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create .env file:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Setup database:
```bash
python manage.py migrate
```

6. Create superuser:
```bash
python manage.py createsuperuser
```

7. Run development server:
```bash
python manage.py runserver
```

## Environment Variables

Create a `.env` file with the following variables:

```
# Django settings
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=content_generator
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=db
DB_PORT=5432

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHANNEL_ID=your-channel-id

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

## Project Structure

```
content_generator/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env
├── content_generator/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── bot/
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── admin.py
│   └── services/
│       ├── openai_service.py
│       └── telegram_service.py
└── templates/
    └── admin/
        └── custom_admin/
```

## Docker Commands

- Start all services:
```bash
docker-compose up
```

- Start in background:
```bash
docker-compose up -d
```

- Stop all services:
```bash
docker-compose down
```

- View logs:
```bash
docker-compose logs -f
```

- Rebuild containers:
```bash
docker-compose up --build
```

- Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

- Create superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

- Access PostgreSQL:
```bash
docker-compose exec db psql -U postgres
```

## License

MIT License