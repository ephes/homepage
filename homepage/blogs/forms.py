from __future__ import absolute_import

from django import forms

from ckeditor.fields import RichTextFormField

from .models import BlogPost


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'content']
