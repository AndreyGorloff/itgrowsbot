from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0004_add_progress_to_post'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='priority',
            field=models.IntegerField(default=0, help_text='Higher number means higher priority'),
        ),
    ] 