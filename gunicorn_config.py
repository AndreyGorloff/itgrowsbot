import multiprocessing

# Количество воркеров
workers = multiprocessing.cpu_count() * 2 + 1

# Бинд
bind = "0.0.0.0:8000"

# Таймауты
timeout = 120
graceful_timeout = 120
keepalive = 5

# Логирование
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Перезапуск воркеров
max_requests = 1000
max_requests_jitter = 50

# Предварительная загрузка приложения
preload_app = True

# Перезапуск при изменении кода
reload = True 