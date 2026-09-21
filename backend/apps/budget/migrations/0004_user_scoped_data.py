from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def get_fallback_user(apps):
    User = apps.get_model("auth", "User")
    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if user:
        return user

    user = User(username="default", password="!")
    user.save()
    return user


def assign_existing_records(apps, schema_editor):
    Category = apps.get_model("budget", "Category")
    ImportTemplate = apps.get_model("budget", "ImportTemplate")
    Statement = apps.get_model("budget", "Statement")
    fallback_user = get_fallback_user(apps)

    Category.objects.filter(user__isnull=True).update(user=fallback_user)
    ImportTemplate.objects.filter(user__isnull=True).update(user=fallback_user)
    Statement.objects.filter(user__isnull=True).update(user=fallback_user)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("budget", "0003_importtemplate"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="statement",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="importtemplate",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(assign_existing_records, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="category",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="statement",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="importtemplate",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="importtemplate",
            name="name",
            field=models.CharField(max_length=120),
        ),
        migrations.AddConstraint(
            model_name="category",
            constraint=models.UniqueConstraint(
                fields=("user", "title"),
                name="unique_category_per_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="importtemplate",
            constraint=models.UniqueConstraint(
                fields=("user", "name"),
                name="unique_import_template_per_user",
            ),
        ),
    ]
