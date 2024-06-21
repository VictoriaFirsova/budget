from django.apps import AppConfig
from django.db.utils import OperationalError


class BudgetConfig(AppConfig):
    name = "apps.budget"

    def ready(self):
        from .models import Category

        categories = [
            "Бензин",
            "Здоровье",
            "Машина",
            "Продукты",
            "Рестораны",
            "Собака",
            "Жилье",
            "Развлечения",
            "Одежда",
            "Красота",
            "Наличные",
            "Доставка",
            "Электроника",
            "Связь",
        ]

        try:
            for category in categories:
                Category.objects.get_or_create(title=category)
        except OperationalError:
            # Handle the case where the database is not ready yet
            pass
