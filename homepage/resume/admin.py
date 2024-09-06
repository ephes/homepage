from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import CVToken


@admin.register(CVToken)
class CVTokenAdmin(admin.ModelAdmin):
    fields = ("receiver",)
    list_display = ("token", "created", "receiver", "token_link")
    search_fields = ("receiver",)

    @admin.display(description="Token Link")
    def token_link(self, obj):
        cv_url = reverse("resume:cv")
        cv_url_with_token = f"{cv_url}?token={obj.token}"
        return format_html('<a href="{}" target="_blank">{}</a>', cv_url_with_token, cv_url_with_token)
