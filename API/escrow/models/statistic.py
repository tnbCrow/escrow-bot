from django.db import models


class Statistic(models.Model):

    total_tnbc = models.IntegerField()

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.total_tnbc} TNBC available!!!'
