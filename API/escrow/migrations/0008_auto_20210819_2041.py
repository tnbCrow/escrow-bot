# Generated by Django 3.2.6 on 2021-08-19 14:56

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('escrow', '0007_auto_20210819_1435'),
    ]

    operations = [
        migrations.CreateModel(
            name='Agent',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('discord_id', models.IntegerField(unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='escrow',
            name='agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='escrow.agent'),
        ),
    ]