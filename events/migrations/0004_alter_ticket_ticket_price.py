# Generated by Django 5.1.6 on 2025-03-01 13:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0003_remove_cartitem_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='ticket_price',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='events.ticketprice'),
        ),
    ]
