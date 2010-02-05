from django.db import models
from django.core.exceptions import ObjectDoesNotExist

from typepadapp.models.users import User


class CrosspostOptions(models.Model):
    """
        Persists the checked state of user's
        crosspost options.
    """
 
    user_id = models.CharField(max_length=100, unique=True, null=False, blank=False)
    crosspost = models.CharField(max_length=2000)
 
    @property
    def user(self):
        return User.get_by_id(self.user_id)

    @classmethod
    def get(cls, key):
        try:
            return cls.objects.get(user_id=key)
        except ObjectDoesNotExist:
            return None

    class Meta:
        app_label = 'motion'
        db_table = 'motion_crosspostoptions'
