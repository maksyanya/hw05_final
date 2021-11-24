import shutil
import tempfile
from django.conf import settings
from django.test import Client
from django.test import TestCase
from django.urls import reverse

# from django import forms
from posts.models import Group
from posts.models import Post
from posts.models import User

from django.test import override_settings

from django.core.files.uploadedfile import SimpleUploadedFile

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

USERNAME = 'test_author'
TITLE = 'test_title'
SLUG = 'test_slug'
DESCRIPTION = 'test_discription'
TEXT = 'test_text'
TITLE_ANOTHER = 'another_title'
SLUG_ANOTHER = 'another_slug'
DESCRIPTION_OTHER = 'other_description'

INDEX_URL = reverse('posts:index')
GROUP_POSTS_URL = reverse('posts:group_posts', kwargs={'slug': SLUG})
PROFILE_URL = reverse('posts:profile', kwargs={'username': USERNAME})


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PictureTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author = User.objects.create(
            username='test_name'
        )

        self.group = Group.objects.create(
            title='Заголовок',
            slug='test_slug',
        )

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        self.post = Post.objects.create(
            author=self.author,
            group=self.group,
            text=TEXT,
            image=self.uploaded,
        )
        self.POST_DETAIL_URL = reverse(
            'posts:post_detail',
            args=[self.post.id])

        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def image(self):
        '''Проверяется картинка.'''
        url_list = [
            INDEX_URL,
            GROUP_POSTS_URL,
            PROFILE_URL,
            self.POST_DETAIL_URL
        ]
        for url in url_list:
            response = self.authorized_client.get(url)
            if 'page_obj' in response.context:
                post = response.context['page_obj'][0]
            else:
                post = response.context['post']
            self.assertEqual(len(['page_obj']), 1)
            self.assertEqual(post.image, self.post.image)
