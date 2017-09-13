from django.contrib import admin

from .models import Blog
from .models import BlogPost


class BlogModelAdmin(admin.ModelAdmin):
       list_display = ('title', 'user')

admin.site.register(Blog, BlogModelAdmin)


class BlogPostModelAdmin(admin.ModelAdmin):
       list_display = ('title', 'author', 'blog')
       class Media:
           js = ('js/ckeditor_fix.js',)

admin.site.register(BlogPost, BlogPostModelAdmin)
