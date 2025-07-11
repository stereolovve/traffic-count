# Generated by Django 5.1.3 on 2025-06-27 18:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tickets", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ticket",
            name="turno",
            field=models.CharField(
                choices=[
                    ("MANHA", "Manhã"),
                    ("TARDE", "Tarde"),
                    ("NOITE", "Noite"),
                    ("INTEGRAL", "Integral"),
                ],
                max_length=10,
                verbose_name="Turno",
            ),
        ),
    ]
