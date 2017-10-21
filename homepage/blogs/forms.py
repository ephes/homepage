from __future__ import absolute_import

from django import forms

from .models import (
    BlogPost,
    BlogImage
)


class BlogPostForm(forms.ModelForm):
    slug = forms.CharField(required=False)

    class Meta:
        model = BlogPost
        fields = ['title', 'content', 'published', 'slug']


class BlogImageForm(forms.ModelForm):
    class Meta:
        model = BlogImage
        fields = ['original']
