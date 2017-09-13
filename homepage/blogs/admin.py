from django.contrib import admin

from .models import Blog
from .models import BlogPost


admin.site.register(Blog)
class BlogModelAdmin(admin.ModelAdmin):
       list_display = ('title', 'user')


admin.site.register(BlogPost)
class BlogPostModelAdmin(admin.ModelAdmin):
       list_display = ('title', 'author', 'blog')
