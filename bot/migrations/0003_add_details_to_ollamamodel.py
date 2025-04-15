from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0002_ollamamodel_alter_openaisettings_local_model_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='ollamamodel',
            name='details',
            field=models.JSONField(default=dict, blank=True, null=True),
        ),
    ] 