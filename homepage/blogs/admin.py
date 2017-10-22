from django.contrib import admin

from .models import Blog
from .models import BlogPost
from .models import BlogImage
from .models import BlogVideo
from .models import BlogMedia
from .models import BlogGallery


class AdminUserMixin:
    def get_changeform_initial_data(self, request):
        return {'user': request.user, 'author': request.user}


class BlogModelAdmin(AdminUserMixin, admin.ModelAdmin):
    list_display = ('title', 'user')


admin.site.register(Blog, BlogModelAdmin)


class BlogPostModelAdmin(AdminUserMixin, admin.ModelAdmin):
    list_display = ('title', 'author', 'blog')

    class Media:
        js = ('js/ckeditor_fix.js',)


admin.site.register(BlogPost, BlogPostModelAdmin)


class ImageModelAdmin(AdminUserMixin, admin.ModelAdmin):
    list_display = ('pk', 'portrait', 'original', 'user')
    fields = ('user', 'original', 'portrait')


admin.site.register(BlogImage, ImageModelAdmin)


class VideoModelAdmin(AdminUserMixin, admin.ModelAdmin):
    list_display = ('pk', 'user')


admin.site.register(BlogVideo, VideoModelAdmin)


class GalleryModelAdmin(AdminUserMixin, admin.ModelAdmin):
    list_display = ('pk',)
    fields = ('user', 'images')


admin.site.register(BlogGallery, GalleryModelAdmin)


class BlogMediaModelAdmin(AdminUserMixin, admin.ModelAdmin):
    list_display = ('pk',)


admin.site.register(BlogMedia, BlogMediaModelAdmin)
