# Generated by Django 5.1.3 on 2024-11-26 20:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autenticacao', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='nome_completo',
            new_name='name',
        ),
        migrations.AlterField(
            model_name='user',
            name='last_name',
            field=models.CharField(max_length=255),
        ),
    ]