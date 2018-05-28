from __future__ import absolute_import

from django import forms
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .models import (
    BlogPost,
    BlogImage,
    BlogVideo,
)


class BlogPostForm(forms.ModelForm):
    is_published = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['title'].widget.attrs['size'] = 80
        self.fields['pub_date'].required = False
        self.fields['pub_date'].widget = forms.DateTimeInput(
            attrs={'type': 'datetime-local'})
        self.fields['pub_date'].label = _('Publication date')
        self.fields['pub_date'].help_text = _('Article will be published after this date.')
        self.fields['visible_date'].required = False
        self.fields['visible_date'].widget = forms.DateTimeInput(
            attrs={'type': 'datetime-local'})
        self.fields['visible_date'].label = _('Visible date')
        self.fields['visible_date'].help_text = _('Date to be shown above article.')

    def _set_pub_date(self, cleaned_data):
        pub_date = cleaned_data.get('pub_date')
        is_published = cleaned_data.get('is_published')
        if pub_date is None and is_published:
            cleaned_data['pub_date'] = timezone.now()
        return cleaned_data

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data = self._set_pub_date(cleaned_data)
        return cleaned_data

    class Meta:
        model = BlogPost
        fields = ['title', 'content', 'pub_date', 'visible_date',
                  'is_published', 'slug']


class BlogImageForm(forms.ModelForm):
    class Meta:
        model = BlogImage
        fields = ['original']


class BlogVideoForm(forms.ModelForm):
    class Meta:
        model = BlogVideo
        fields = ['original']
