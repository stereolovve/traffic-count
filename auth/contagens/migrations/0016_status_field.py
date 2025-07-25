from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("contagens", "0015_session_responsavel_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="session",
            name="ativa",
        ),
        migrations.AddField(
            model_name="session",
            name="status",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("Aguardando", "Aguardando"),
                    ("Em andamento", "Em andamento"),
                    ("Concluída", "Concluída"),
                ],
                default="Aguardando",
            ),
        ),
    ] 