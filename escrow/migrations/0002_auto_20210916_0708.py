# Generated by Django 3.2.6 on 2021-09-16 01:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escrow', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='escrow',
            name='amount',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='escrow',
            name='fee',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='escrowuser',
            name='total_disputes',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='escrowuser',
            name='total_escrows',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='escrowuser',
            name='total_tnbc_escrowed',
            field=models.BigIntegerField(default=0),
        ),
    ]
