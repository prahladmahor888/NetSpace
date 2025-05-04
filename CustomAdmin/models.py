from django.db import models
from Accounts.models import CustomUser

class Visitor(models.Model):
    """
    Stores information about each site visitor for analytics and security purposes.
    """
    ip_address = models.GenericIPAddressField(db_index=True, verbose_name="IP Address")
    user_agent = models.CharField(max_length=255, verbose_name="User Agent")
    visit_time = models.DateTimeField(auto_now_add=True, verbose_name="Visit Time")
    referrer = models.URLField(blank=True, null=True, verbose_name="Referrer")
    session_key = models.CharField(max_length=40, blank=True, null=True, verbose_name="Session Key")
    user = models.ForeignKey(
        CustomUser, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="User"
    )

    class Meta:
        ordering = ['-visit_time']
        verbose_name = "Visitor"
        verbose_name_plural = "Visitors"

    def __str__(self):
        user_info = f" (User: {self.user})" if self.user else ""
        return f"Visitor {self.ip_address}{user_info} at {self.visit_time.strftime('%Y-%m-%d %H:%M:%S')}"

    def get_location(self):
        """
        Placeholder for future IP geolocation logic.
        """
        return None

    @classmethod
    def total_count(cls):
        """Returns the total number of visitor records."""
        return cls.objects.count()

    @classmethod
    def unique_ip_count(cls):
        """Returns the count of unique IP addresses."""
        return cls.objects.values('ip_address').distinct().count()

    @classmethod
    def unique_user_count(cls):
        """Returns the count of unique authenticated users."""
        return cls.objects.exclude(user=None).values('user').distinct().count()