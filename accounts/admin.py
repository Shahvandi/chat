from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from .models import User, Otp


class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    # form = UserChangeForm
    # add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ["mobile", "is_admin"]
    list_filter = ["is_admin"]
    fieldsets = [
        (None, {"fields": ["mobile", "fullname", "email", "password"]}),
        ("دسترسی ها", {"fields": ["is_active", "is_admin"]}),
    ]
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["mobile", "fullname", "email", "password1", "password2"],
            },
        ),
    ]
    search_fields = ["mobile"]
    ordering = ["mobile"]
    filter_horizontal = []


admin.site.unregister(Group)


admin.site.register(User, UserAdmin)
admin.site.register(Otp)
