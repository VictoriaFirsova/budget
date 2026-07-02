from ..components.common import *  # noqa: F403  # Импортируем общие настройки

# Настройки для подключения к базе данных MySQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "test",  # Имя базы данных
        "USER": "admin",  # Имя пользователя
        "PASSWORD": "3904",  # Пароль
        "HOST": "localhost",  # Хост
        "PORT": "3306",  # Порт
    }
}

# Дополнительные настройки для тестирования
DEBUG = False  # Выключаем режим отладки для тестов
# Настройки логирования
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}
