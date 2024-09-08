from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import CVToken, Person, Project, Timeline, TimelineEntry


@admin.register(CVToken)
class CVTokenAdmin(admin.ModelAdmin):
    fields = ("person", "receiver")
    list_display = ("person", "token", "created", "receiver", "token_link")
    search_fields = ("receiver",)

    @admin.display(description="Token Link")
    def token_link(self, obj):
        cv_url = reverse("resume:cv", kwargs={"slug": obj.person.slug})
        cv_url_with_token = f"{cv_url}?token={obj.token}"
        return format_html('<a href="{}" target="_blank">{}</a>', cv_url_with_token, cv_url_with_token)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    fields = (
        "name",
        "slug",
        "pronouns",
        "tagline",
        "about",
        "avatar_url",
        "avatar_alt",
        "location_name",
        "location_url",
        "email",
        "phone",
        "website",
        "github",
        "linkedin",
        "mastodon",
        "skills",
        "education_school_name",
        "education_school_url",
        "education_start",
        "education_end",
    )


@admin.register(Timeline)
class TimelineAdmin(admin.ModelAdmin):
    fields = ("person", "title", "position")


@admin.register(TimelineEntry)
class TimelineEntryAdmin(admin.ModelAdmin):
    fields = (
        "timeline",
        "company_name",
        "company_url",
        "role",
        "start",
        "end",
        "description",
        "badges",
        "position",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # If this is a new entry, prepopulate the position field
        if obj is None:
            timeline_id = request.GET.get("timeline")
            if timeline_id:
                last_position = (
                    TimelineEntry.objects.filter(timeline=timeline_id)
                    .order_by("-position")
                    .values_list("position", flat=True)
                    .first()
                )
                next_position = (last_position or 0) + 1
                form.base_fields["position"].initial = next_position

        return form


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    fields = (
        "person",
        "title",
        "url",
        "description",
        "badges",
        "position",
    )
