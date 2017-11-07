import logging

from django.contrib import admin

from .models import Blog
from .models import BlogPost
from .models import BlogFile
from .models import BlogImage
from .models import BlogVideo
from .models import BlogGallery

logger = logging.getLogger(__name__)


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
    list_display = ('pk', 'original', 'user')
    fields = ('user', 'original')


admin.site.register(BlogImage, ImageModelAdmin)


class BlogFileAdmin(AdminUserMixin, admin.ModelAdmin):
    list_display = ('original', 'user')
    fields = ('user', 'original')


admin.site.register(BlogFile, BlogFileAdmin)


class VideoModelAdmin(AdminUserMixin, admin.ModelAdmin):
    list_display = ('pk', 'user')

    def save_model(self, request, obj, form, change):
        logger.info('poster: {}'.format(obj.poster))
        logger.info('form: {}'.format(form.cleaned_data))
        if change and not form.cleaned_data['poster']:
            logger.info('poster was cleared')
            obj.calc_poster = False
        super().save_model(request, obj, form, change)


admin.site.register(BlogVideo, VideoModelAdmin)


class GalleryModelAdmin(AdminUserMixin, admin.ModelAdmin):
    list_display = ('pk',)
    fields = ('user', 'images')


admin.site.register(BlogGallery, GalleryModelAdmin)
