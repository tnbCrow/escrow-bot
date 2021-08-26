# Generated by Django 3.2.6 on 2021-08-17 03:19

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('confirmation_status', models.CharField(choices=[('WAITING_CONFIRMATION', 'Waiting Confirmation'), ('CONFIRMED', 'Confirmed')], max_length=255)),
                ('direction', models.CharField(choices=[('INCOMING', 'Incoming'), ('OUTGOING', 'Outgoing')], max_length=255)),
                ('transaction_status', models.CharField(choices=[('NEW', 'New'), ('IDENTIFIED', 'Identified'), ('UNIDENTIFIED', 'Unidentified'), ('REFUNDED', 'Refunded')], max_length=255)),
                ('account_number', models.CharField(max_length=64)),
                ('amount', models.IntegerField()),
                ('fee', models.IntegerField(default=0)),
                ('signature', models.CharField(max_length=255)),
                ('block', models.CharField(max_length=255)),
                ('memo', models.CharField(max_length=255)),
                ('total_confirmations', models.IntegerField(default=0)),
                ('remarks', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('discord_id', models.IntegerField(unique=True)),
                ('balance', models.IntegerField(default=0)),
                ('locked', models.IntegerField(default=0)),
                ('memo', models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Escrow',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount', models.IntegerField()),
                ('status', models.CharField(choices=[('OPEN', 'Open'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled'), ('ADMIN_SETTLED', 'Admin Settled'), ('ADMIN_CANCELLED', 'Admin Cancelled')], max_length=255)),
                ('initiator', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='initiator', to='escrow.user')),
                ('successor', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='successor', to='escrow.user')),
            ],
        ),
    ]