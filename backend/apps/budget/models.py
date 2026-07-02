from django.conf import settings
from django.db import models


class Category(models.Model):
    """Модель категории."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=250)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "categories"
        app_label = "budget"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "title"], name="unique_category_per_user"
            ),
        ]

    objects = models.Manager()


class Statement(models.Model):
    """Модель операции"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    operation_name = models.CharField(max_length=200)
    amount = models.DecimalField(decimal_places=2, max_digits=15)
    currency = models.CharField(max_length=3)
    category = models.CharField(max_length=400)
    my_category = models.ForeignKey(Category, null=True, on_delete=models.SET_NULL)
    card = models.CharField(max_length=30, default="Unknown")

    def __str__(self):
        return f"{self.date} {self.amount}"

    class Meta:
        app_label = "budget"

    objects = models.Manager()


class ImportTemplate(models.Model):
    """Saved statement import column mapping."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    columns = models.JSONField(default=dict)
    amount_sign = models.CharField(max_length=20, default="as_is")
    dayfirst = models.BooleanField(default=True)
    skip_rows = models.PositiveIntegerField(default=0)
    skip_after_header = models.PositiveIntegerField(default=0)
    default_currency = models.CharField(max_length=3, blank=True, default="")
    default_card = models.CharField(max_length=30, blank=True, default="")
    header_signature = models.CharField(max_length=500, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = "budget"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_import_template_per_user"
            ),
        ]

    objects = models.Manager()
