# Generated by Django 5.1.6 on 2025-04-05 00:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_alter_ticketprice_name'),
        ('payment', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='servicefee',
            unique_together={('event', 'ticket_price')},
        ),
    ]
