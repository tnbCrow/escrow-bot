# Generated by Django 3.2.6 on 2021-09-12 06:46

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20210912_1155'),
    ]

    operations = [
        migrations.CreateModel(
            name='ThenewbostonWallet',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('balance', models.IntegerField(default=0)),
                ('locked', models.IntegerField(default=0)),
                ('memo', models.CharField(max_length=255, unique=True)),
                ('withdrawal_address', models.CharField(blank=True, max_length=64, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='core.user')),
            ],
        ),
    ]