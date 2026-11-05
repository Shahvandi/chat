from django.contrib import admin
from .models import User, Otp


@admin.register(User)
class UserModelAdmin(admin.ModelAdmin):
    list_display  = ("mobile", "is_active", "date_joined")
    list_filter   = ("is_active", )
    search_fields = ("mobile", )


@admin.register(Otp)
class OtpAdmin(admin.ModelAdmin):
    list_display  = ("mobile", "code", "created_at")
    search_fields = ("mobile", )