from django.db import models

# Create your models here.


# EventView Model
class EventView(models.Model):
    session_key = models.CharField(max_length=40, null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)


   