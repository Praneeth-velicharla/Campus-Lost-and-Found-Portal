from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class LostItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    features = models.TextField()
    photo = models.ImageField(upload_to='lost_photos/', blank=True, null=True)
    date_reported = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Lost Items"

    def __str__(self):
        return f"{self.name} (by {self.user.username})"


class FoundItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    features = models.TextField()
    photo = models.ImageField(upload_to='found_photos/')
    date_reported = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Found Items"

    def __str__(self):
        return f"{self.name} (by {self.user.username})"



# 1. NEW: UserProfile Model (To store phone number)
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signal to create/update UserProfile when a User is created/saved
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # This prevents the signal from failing if the user is saved before the profile is created in a complex scenario
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()

# 2. MatchNotificationStatus Model (from previous step)
class MatchNotificationStatus(models.Model):
    lost_item = models.ForeignKey(LostItem, on_delete=models.CASCADE)
    found_item = models.ForeignKey(FoundItem, on_delete=models.CASCADE)
    notified_user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('ACCEPTED', 'Match Accepted'),
        ('IGNORED', 'Match Ignored'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('lost_item', 'found_item', 'notified_user')
        verbose_name_plural = "Match Notification Statuses"

    def __str__(self):
        return f"{self.notified_user.username}: {self.lost_item.name} vs {self.found_item.name} ({self.status})"