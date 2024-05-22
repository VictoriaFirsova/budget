import os
import django
import sys

# Добавляем корневую директорию проекта в список путей поиска Python
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Добавляем путь к папке apps в список путей поиска Python
APPS_DIR = os.path.join(BASE_DIR, 'apps')
sys.path.append(APPS_DIR)

# Путь к файлу настроек Django для тестирования с MySQL и другими настройками
SETTINGS_MODULE = 'backend.server.settings.environments.testing'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', SETTINGS_MODULE)
django.setup()