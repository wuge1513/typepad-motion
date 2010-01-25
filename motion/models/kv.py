from django_kvstore import models

class CrosspostOptions(models.Model):
    """
        Persists the checked state of user's
        crosspost options.
    """

    user_id = models.Field(pk=True)
    crosspost = models.Field()

    @property
    def user(self):
        return User.get_by_id(self.user_id)
