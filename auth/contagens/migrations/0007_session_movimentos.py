# Generated by Django 5.1.3 on 2025-03-23 20:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contagens', '0006_alter_session_data_alter_session_horario_inicio'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='movimentos',
            field=models.JSONField(default=list),
        ),
    ]
