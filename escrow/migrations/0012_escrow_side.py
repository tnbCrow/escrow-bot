# Generated by Django 3.2.7 on 2021-12-12 09:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escrow', '0011_advertisement_side'),
    ]

    operations = [
        migrations.AddField(
            model_name='escrow',
            name='side',
            field=models.CharField(choices=[('BUY', 'Buy'), ('SELL', 'Sell')], default='SELL', max_length=255),
            preserve_default=False,
        ),
    ]