from django.db import models

# Create your models here.


class DevicesInfo(models.Model):
    ip = models.CharField(max_length=15, primary_key=True, null=False)
    interfaces = models.TextField(null=True)
    interfaces_date = models.DateTimeField(null=True)
    sys_info = models.TextField(null=True)
    sys_info_date = models.DateTimeField(null=True)
    vlans = models.TextField(null=True)
    vlans_date = models.DateTimeField(null=True)
    device_name = models.CharField(max_length=100, null=True)

    class Meta:
        db_table = 'device_info'
        ordering = ('ip',)
