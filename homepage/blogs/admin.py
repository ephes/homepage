from django.contrib import admin

from .models import Blog
from .models import BlogPost
from .models import BlogImage
from .models import BlogVideo


class BlogModelAdmin(admin.ModelAdmin):
    list_display = ('title', 'user')

admin.site.register(Blog, BlogModelAdmin)


class BlogPostModelAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'blog')

    class Media:
        js = ('js/ckeditor_fix.js',)

admin.site.register(BlogPost, BlogPostModelAdmin)


class ImageModelAdmin(admin.ModelAdmin):
    list_display = ('pk', 'portrait', 'original', 'user')


admin.site.register(BlogImage, ImageModelAdmin)


class VideoModelAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user')


admin.site.register(BlogVideo, VideoModelAdmin)
