from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("budget", "0004_user_scoped_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="importtemplate",
            name="skip_after_header",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="importtemplate",
            name="skip_rows",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
