# Generated by Django 3.2.7 on 2021-11-18 14:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escrow', '0009_auto_20211117_0725'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='escrow',
            name='initiator_cancelled',
        ),
        migrations.RemoveField(
            model_name='escrow',
            name='successor_cancelled',
        ),
        migrations.AddField(
            model_name='escrow',
            name='conversation_channel_id',
            field=models.CharField(default='None', max_length=255),
            preserve_default=False,
        ),
    ]
