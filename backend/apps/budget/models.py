from django.db import models


class Category(models.Model):
    """Модель категории."""

    title = models.CharField(max_length=250)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "categories"


class Statement(models.Model):
    """Модель операции"""

    date = models.DateField()
    operation_name = models.CharField(max_length=200)
    amount = models.DecimalField(decimal_places=2, max_digits=15)
    currency = models.CharField(max_length=3)
    category = models.CharField(max_length=400)
    my_category = models.ForeignKey(Category, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.date} {self.amount}"
