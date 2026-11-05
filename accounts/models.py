import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserModelManager(BaseUserManager):
    def create_user(self, mobile, password=None, **extra):
        if not mobile:
            raise ValueError("Mobile is required.")
        user = self.model(mobile=mobile, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(mobile, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile      = models.CharField(max_length=20, unique=True)
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True,null=True,blank=True)

    objects = UserModelManager()

    USERNAME_FIELD  = "mobile"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.mobile


class Otp(models.Model):
    """
    Stores one active OTP per mobile. Expiry is checked in the repository
    using OTP_EXPIRY_SECONDS from settings.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile     = models.CharField(max_length=20, unique=True)
    code       = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OTP<{self.mobile}>"
