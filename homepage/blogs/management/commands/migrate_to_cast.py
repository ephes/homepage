from django.db import connection
from django.core.management.base import BaseCommand

from cast.models import (
    Blog as CastBlog,
    Image,
    Video,
    File,
    Post,
    Gallery,
)

from homepage.blogs.models import (
    Blog,
    BlogImage,
    BlogFile,
    BlogGallery,
    BlogPost,
    BlogVideo,
)


class Command(BaseCommand):
    help = ("migrate to django-cast")

    def reset_auto_increment(self, model, seq):
        new_pk = max([pk for pk, in model.objects.values_list("pk")]) + 1
        with connection.cursor() as cur:
            cur.execute(f"ALTER SEQUENCE {seq} RESTART WITH {new_pk}")

    def migrate_blogs(self):
        CastBlog.objects.all().delete()
        blog_attrs = ("pk", "user", "title", "description", "slug", "created", "modified")
        cast_blogs = []
        for bl in Blog.objects.all():
            params = {attr: getattr(bl, attr) for attr in blog_attrs}
            cast_blogs.append(CastBlog(**params))
        created = CastBlog.objects.bulk_create(cast_blogs)
        self.reset_auto_increment(CastBlog, "cast_blog_id_seq")
        print("Migrated blogs: ", CastBlog.objects.count())

    def migrate_images(self):
        Image.objects.all().delete()
        image_attrs = ("pk", "original", "original_height", "original_width", "user",
                       "created", "modified")
        cast_images = []
        for bi in BlogImage.objects.all():
            params = {attr: getattr(bi, attr) for attr in image_attrs}
            cast_images.append(Image(**params))
        created = Image.objects.bulk_create(cast_images)
        self.reset_auto_increment(Image, "cast_image_id_seq")
        print("Migrated images: ", Image.objects.count())

    def migrate_videos(self):
        Video.objects.all().delete()
        video_attrs = ("pk", "original", "poster", "poster_seconds", "user",
                       "created", "modified")
        cast_videos = []
        for bv in BlogVideo.objects.all():
            params = {attr: getattr(bv, attr) for attr in video_attrs}
            cast_videos.append(Video(**params))
        created = Video.objects.bulk_create(cast_videos)
        self.reset_auto_increment(Video, "cast_video_id_seq")
        print("Migrated videos: ", Video.objects.count())

    def migrate_files(self):
        File.objects.all().delete()
        file_attrs = ("pk", "original", "user", "created", "modified")
        cast_files = []
        for bf in BlogFile.objects.all():
            params = {attr: getattr(bf, attr) for attr in file_attrs}
            cast_files.append(File(**params))
        created = File.objects.bulk_create(cast_files)
        self.reset_auto_increment(File, "cast_file_id_seq")
        print("Migrated files: ", File.objects.count())

    def migrate_galleries(self):
        Gallery.objects.all().delete()
        gallery_attrs = ("pk", "user", "created", "modified")
        for bg in BlogGallery.objects.all():
            params = {attr: getattr(bg, attr) for attr in gallery_attrs}
            gallery = Gallery.objects.create(**params)
            img_pks = [pk for pk, in bg.images.values_list("pk")]
            images = Image.objects.filter(pk__in=img_pks)
            for image in images:
                gallery.images.add(image)
        self.reset_auto_increment(Gallery, "cast_gallery_id_seq")
        print("Migrated galleries: ", Gallery.objects.count())

    def migrate_posts(self):
        Post.objects.all().delete()
        post_attrs = ("pk", "author", "title", "pub_date", "visible_date",
                      "content", "slug", "created", "modified")
        for bp in BlogPost.objects.all():
            params = {attr: getattr(bp, attr) for attr in post_attrs}
            params["content"] = (params["content"].replace("blog_image", "image")
                                                  .replace("blog_gallery", "gallery")
                                                  .replace("blog_video", "video"))
            params["blog"] = CastBlog.objects.get(pk=bp.blog.pk)
            post = Post.objects.create(**params)
            
            img_pks = [pk for pk, in bp.images.values_list("pk")]
            images = Image.objects.filter(pk__in=img_pks)
            for image in images:
                post.images.add(image)
            
            video_pks = [pk for pk, in bp.videos.values_list("pk")]
            videos = Video.objects.filter(pk__in=video_pks)
            for video in videos:
                post.videos.add(video)

            gallery_pks = [pk for pk, in bp.galleries.values_list("pk")]
            galleries = Gallery.objects.filter(pk__in=gallery_pks)
            for gallery in galleries:
                post.galleries.add(gallery)
        self.reset_auto_increment(Post, "cast_post_id_seq")
        print("Migrated posts: ", Post.objects.count())

    def handle(self, *args, **options):
        self.migrate_blogs()
        self.migrate_images()
        self.migrate_videos()
        self.migrate_files()
        self.migrate_galleries()
        self.migrate_posts()
