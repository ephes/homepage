from __future__ import absolute_import

from django import forms

from .models import (
    BlogPost,
    BlogImage,
    BlogVideo,
)


class BlogPostForm(forms.ModelForm):
    slug = forms.CharField(required=False)

    class Meta:
        model = BlogPost
        fields = ['title', 'content', 'published', 'pub_date', 'slug']


class BlogImageForm(forms.ModelForm):
    class Meta:
        model = BlogImage
        fields = ['original']


class BlogVideoForm(forms.ModelForm):
    class Meta:
        model = BlogVideo
        fields = ['original']
