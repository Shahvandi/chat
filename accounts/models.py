from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
import uuid


class UserManager(BaseUserManager):
    def create_user(self, mobile=None, email=None, fullname=None, password=None):

        user = self.model()
        user.mobile = mobile
        user.email = email
        user.fullname = fullname
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, email, fullname, password=None):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(mobile, email, fullname, password=password)
        user.is_superuser = True
        user.is_admin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile = models.CharField(max_length=11, unique=True, verbose_name='تلفن همراه')
    email = models.EmailField(
        verbose_name='آدرس ایمیل',
        max_length=255,
        null=True,
        blank=True,
        unique=True,
    )
    fullname = models.CharField(max_length=60,  verbose_name='نام و نام خانوادگی')
    is_active = models.BooleanField(default=True,  verbose_name='فعال')
    is_admin = models.BooleanField(default=False, verbose_name='ادمین')

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['phone', 'fullname']

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return self.fullname

    def has_perm(self, perm, obj=None):
        """Does the user have a specific permission?"""
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        """Does the user have permissions to view the app `app_label`?"""
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        # "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin


# SMS verification Model:
class Otp(models.Model):
    mobile = models.CharField(max_length=11)
    token = models.CharField(max_length=100,unique=True, null=True)
    code = models.SmallIntegerField()
    expiration_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.mobile

    class Meta:
        verbose_name = 'کد'
        verbose_name_plural = 'کدها'
