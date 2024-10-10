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


# @admin.register(Person)
# class PersonAdmin(admin.ModelAdmin):
#     fields = (
#         "name",
#         "slug",
#         "pronouns",
#         "tagline",
#         "about",
#         "avatar_url",
#         "avatar_alt",
#         "location_name",
#         "location_url",
#         "email",
#         "phone",
#         "website",
#         "github",
#         "linkedin",
#         "mastodon",
#         "skills",
#         "education_school_name",
#         "education_school_url",
#         "education_start",
#         "education_end",
#     )
#
#     def get_inline_instances(self, request, obj=None):
#         from .plugins import plugin_registry
#         inline_instances = super().get_inline_instances(request, obj)
#         for plugin in plugin_registry.get_all_plugins():
#             inline_class = plugin.get_admin_inline()
#             if inline_class:
#                 inline_instances.append(inline_class(self.model, self.admin_site))
#         return inline_instances


from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path

from .plugins import plugin_registry


class PersonAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        self.list_display = ["name"]
        print("get all plugins: ", plugin_registry.get_all_plugins())
        self.readonly_fields = []
        for plugin in plugin_registry.get_all_plugins():
            self.list_display.append(plugin.get_list_display_field())
        super().__init__(model, admin_site)

    def add_plugin_method(self, plugin):
        """
        Add a method to the admin class that will return a link to the plugin admin view.
        This is used to have the plugins show up as readonly fields in the person change view.
        """

        def plugin_method(_self, obj):
            return plugin.get_admin_link(obj.id)

        plugin_method.__name__ = plugin.name
        setattr(self.__class__, plugin.name, plugin_method)

    def get_readonly_fields(self, request, obj=None):
        """Add a readonly field for each plugin."""
        readonly_fields = super().get_readonly_fields(request, obj)
        # Filter out all plugins already in readonly_fields - somehow this method is getting called multiple times
        readonly_fields_lookup = set(readonly_fields)
        new_plugins = [p for p in plugin_registry.get_all_plugins() if p.name not in readonly_fields_lookup]
        for plugin in new_plugins:
            readonly_fields.append(plugin.name)
            self.add_plugin_method(plugin)
        return readonly_fields

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:person_id>/plugin/<str:plugin_name>/",
                self.admin_site.admin_view(self.plugin_view),
                name="person-plugin",
            ),
            path(
                "<int:person_id>/plugin/<str:plugin_name>/post/",
                self.admin_site.admin_view(self.plugin_view_post),
                name="person-plugin-post",
            ),
        ]
        return custom_urls + urls

    def plugin_view_post(self, request, person_id, plugin_name):
        person = get_object_or_404(Person, id=person_id)
        plugin = plugin_registry.get_plugin(plugin_name)

        form_class = plugin.get_admin_form()
        if request.method == "POST":
            form = form_class(request.POST)
            if form.is_valid():
                existing_data = plugin.get_data(person)
                existing_data.append(form.cleaned_data)
                plugin.set_data(person, existing_data)
                messages.success(request, f"{plugin.verbose_name} data updated successfully.")
                return redirect("admin:resume_person_change", person_id)
        return redirect("admin:resume_person_change", person_id)

    def plugin_view(self, request, person_id, plugin_name):
        person = get_object_or_404(Person, id=person_id)
        plugin = plugin_registry.get_plugin(plugin_name)

        if not plugin:
            return redirect("admin:resume_person_change", person_id)

        form_class = plugin.get_admin_form()
        forms = []
        if request.method == "POST":
            form = form_class(request.POST)
            if form.is_valid():
                plugin.set_data(person, form.cleaned_data)
                messages.success(request, f"{plugin.verbose_name} data updated successfully.")
                return redirect("admin:resume_person_change", person_id)
        else:
            # initial_data = {'timeline_items': plugin.get_data(person)}
            initial_data = plugin.get_data(person)
            print("initial_data: ", initial_data)
            print("form_class: ", form_class)
            post_url = reverse("admin:person-plugin-post", kwargs={"person_id": person_id, "plugin_name": plugin_name})
            for form_data in initial_data:
                form = form_class(initial=form_data)
                form.post_url = post_url
                forms.append(form)
            if len(forms) == 0:
                form = form_class(initial={})
                form.post_url = post_url
                forms.append(form)
            # form = form_class(initial=initial_data)

        print("post url: ", forms[0].post_url)
        context = {
            "title": f"{plugin.verbose_name} for {person.name}",
            "form": form,
            "forms": forms,
            "formset": form,
            "person": person,
            "plugin": plugin,
            "opts": self.model._meta,
            # context for admin/change_form.html template
            "add": False,
            "change": True,
            "is_popup": False,
            "save_as": False,
            "has_add_permission": False,
            "has_view_permission": True,
            "has_change_permission": True,
            "has_delete_permission": False,
            "has_editable_inline_admin_formsets": False,
        }
        return render(request, plugin.change_form_template, context)


def register_person_admin_after_plugins_are_registered():
    admin.site.register(Person, PersonAdmin)


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
