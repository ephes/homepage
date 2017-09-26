from django.contrib import admin

from .models import Blog
from .models import BlogPost
from .models import BlogImage
from .models import BlogVideo


class AdminUserMixin:
    user_fields = ['user', 'author']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field_name in self.user_fields:
            if field_name in form.base_fields:
                form.base_fields[field_name].initial = request.user
        return form


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
