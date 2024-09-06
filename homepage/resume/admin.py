from django.contrib import admin

from .models import CVToken


@admin.register(CVToken)
class CVTokenAdmin(admin.ModelAdmin):
    fields = ("receiver",)
    list_display = ("token", "created", "receiver")
    search_fields = ("receiver",)
