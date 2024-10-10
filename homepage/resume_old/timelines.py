import json

from django import forms

from .plugins import BasePlugin, plugin_registry


class FreelanceTimelinePlugin(BasePlugin):
    name = "freelance_timeline"
    verbose_name = "Freelance Timeline"
    change_form_template = "resume/admin/timeline_change_admin.html"

    def get_admin_form(self):
        class FreelanceTimelineForm(forms.Form):
            timeline_items = forms.CharField(widget=forms.HiddenInput(), required=False)

            def __init__(self, *args, **kwargs):
                initial = kwargs.get('initial', {})
                if 'timeline_items' in initial and isinstance(initial['timeline_items'], list):
                    initial['timeline_items'] = json.dumps(initial['timeline_items'])
                super().__init__(*args, **kwargs)

            def clean_timeline_items(self):
                items = self.cleaned_data.get('timeline_items')
                if not items:
                    return []
                try:
                    return json.loads(items)
                except json.JSONDecodeError:
                    raise forms.ValidationError("Invalid JSON data for timeline items")

        return FreelanceTimelineForm

    def get_data(self, person):
        return person.data.get(self.name, [])

    def set_data(self, person, data):
        if not person.data:
            person.data = {}
        person.data[self.name] = data.get('timeline_items', [])
        person.save()


class EmployedTimelineForm(forms.Form):
    title = forms.CharField(widget=forms.TextInput())
    description = forms.CharField(widget=forms.Textarea())
    start = forms.CharField(widget=forms.TextInput(), required=False)
    end = forms.CharField(widget=forms.TextInput(), required=False)

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if 'timeline_items' in initial and isinstance(initial['timeline_items'], list):
            initial['timeline_items'] = json.dumps(initial['timeline_items'])
        super().__init__(*args, **kwargs)

    def clean_timeline_items(self):
        items = self.cleaned_data.get('timeline_items')
        if not items:
            return []
        try:
            return json.loads(items)
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON data for timeline items")


EmployedTimelineFormset = forms.formset_factory(form=EmployedTimelineForm, extra=1)


class EmployedTimelinePlugin(BasePlugin):
    name = "employed_timeline"
    verbose_name = "Employed Timeline"
    change_form_template = "resume/admin/timeline_admin_change_formset_htmx.html"

    def get_admin_form(self):
        # return EmployedTimelineFormset
        return EmployedTimelineForm

    def get_data(self, person):
        return person.data.get(self.name, [])

    def set_data(self, person, data):
        if not person.data:
            person.data = {}
        person.data[self.name] = data
        person.save()
