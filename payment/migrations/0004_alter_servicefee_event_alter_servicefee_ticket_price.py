# Generated by Django 5.1.6 on 2025-03-10 11:51

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0004_alter_ticket_ticket_price'),
        ('payment', '0003_servicefee_ticket_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicefee',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_fees', to='events.event'),
        ),
        migrations.AlterField(
            model_name='servicefee',
            name='ticket_price',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.ticketprice'),
        ),
    ]
