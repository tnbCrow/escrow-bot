# Generated by Django 3.2.6 on 2021-09-16 15:57

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20210916_0708'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='scantracker',
            name='id',
        ),
        migrations.AddField(
            model_name='scantracker',
            name='title',
            field=models.CharField(default='main', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='scantracker',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AddField(
            model_name='statistic',
            name='title',
            field=models.CharField(default='main', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='scantracker',
            name='total_scans',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='statistic',
            name='total_balance',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='statistic',
            name='total_fees_collected',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='statistic',
            name='total_servers',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='statistic',
            name='total_users',
            field=models.IntegerField(default=0),
        ),
    ]