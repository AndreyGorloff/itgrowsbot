from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0003_add_details_to_ollamamodel'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='progress',
            field=models.IntegerField(default=0, help_text='Progress of content generation (0-100)', verbose_name='Generation Progress'),
        ),
    ] 