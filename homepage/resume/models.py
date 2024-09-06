import random
import string

from django.db import models


def generate_random_string(length=20):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class CVToken(models.Model):
    """
    Model to store tokens for accessing the CV. The token is just a random string.
    If you want to give someone access to the CV, you can generate a token and send it to them.
    Please note the receiver in the model so you know who you gave access to.
    """

    token = models.CharField(max_length=255, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    receiver = models.CharField(max_length=255)

    def __str__(self):
        return self.token

    def save(self, *args, **kwargs):
        self.token = generate_random_string()
        super().save(*args, **kwargs)
