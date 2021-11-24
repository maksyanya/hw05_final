import shutil
import tempfile

from django.core.cache import cache
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from posts.models import Follow
from posts.models import Group
from posts.models import Post
from posts.models import User
from posts.settings import POSTS_PER_PAGE


USERNAME = 'test_author'
TITLE = 'test_title'
SLUG = 'test_slug'
DESCRIPTION = 'test_discription'
TEXT = 'test_text'
TITLE_ANOTHER = 'another_title'
SLUG_ANOTHER = 'another_slug'
DESCRIPTION_OTHER = 'other_description'

INDEX_URL = reverse('posts:index')
POST_CREATE_URL = reverse('posts:post_create')
GROUP_POSTS_URL = reverse('posts:group_posts', kwargs={'slug': SLUG})
PROFILE_URL = reverse('posts:profile', kwargs={'username': USERNAME})
ANOTHER_GROUP = reverse('posts:group_posts', kwargs={'slug': SLUG_ANOTHER})
FOLLOW_INDEX_URL = reverse('posts:follow_index')

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username=USERNAME)
        cls.group = Group.objects.create(title=TITLE,
                                         slug=SLUG,
                                         description=DESCRIPTION)
        cls.another_group = Group.objects.create(title=TITLE_ANOTHER,
                                                 slug=SLUG_ANOTHER,
                                                 description=DESCRIPTION_OTHER)

        cls.follower = User.objects.create(username='test_follower')
        cls.PROFILE_FOLLOW_URL = reverse(
            'posts:profile_follow',
            kwargs={'username': cls.follower})
        cls.PROFILE_UNFOLLOW_URL = reverse(
            'posts:profile_unfollow',
            kwargs={'username': cls.follower})
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text=TEXT,
            image=cls.uploaded,
        )
        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)

    def test_show_correct_context(self):
        '''Проверяется контекст шаблонов на соответствие.'''
        url_list = [
            INDEX_URL,
            GROUP_POSTS_URL,
            PROFILE_URL,
            self.POST_DETAIL_URL
        ]
        for url in url_list:
            response = self.authorized_client.get(url)
            if 'page_obj' in response.context:
                self.assertEqual(len(response.context['page_obj']), 1)
                post = response.context['page_obj'][0]
            else:
                post = response.context['post']
            self.assertEqual(post.group, self.post.group)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.id, self.post.id)
            self.assertEqual(post.image, self.post.image)

    def test_post_not_in_another_group(self):
        '''Проверяется, что пост не отображается в другой группе'''
        response_group = self.authorized_client.get(ANOTHER_GROUP)
        self.assertNotIn(self.post, response_group.context['page_obj'])

    def test_author_in_profile_page(self):
        '''Проверяется, что автор на станице профиля.'''
        response_author = self.authorized_client.get(PROFILE_URL)
        self.assertEqual(self.author, response_author.context['author'])

    def test_group_in_group_posts_page_(self):
        '''Проверяется, что "группа" на странице групп-ленты..'''
        response = self.authorized_client.get(GROUP_POSTS_URL)
        group = response.context['group']
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(group.description, self.group.description)
        self.assertEqual(group.slug, self.group.slug)
        self.assertEqual(group.id, self.group.id)

    def test_cash_in_index_page(self):
        '''Проверяется работа кэша на главной странице.'''
        response = self.authorized_client.get(INDEX_URL)
        before_records_delete = response.content
        Post.objects.all().delete()
        response = self.authorized_client.get(INDEX_URL)
        after_records_delete = response.content
        self.assertEqual(before_records_delete, after_records_delete)
        cache.clear()
        response = self.authorized_client.get(INDEX_URL)
        after_cache_clearing = response.content
        self.assertNotEqual(after_cache_clearing, before_records_delete)

    def test_authorized_user_can_follow_on_users(self):
        '''Авторизованный пользователь может подписываться
           на других пользователей.
        '''
        self.authorized_client.post(self.PROFILE_FOLLOW_URL)
        follow = Follow.objects.first()
        self.assertEqual(Follow.objects.count(), 1)
        self.assertEqual(follow.author, self.follower)
        self.assertEqual(follow.user, self.author)

    def test_authorized_user_can_unfollow_from_users(self):
        '''Авторизованный пользователь может отписывается
           от других пользователей.
        '''
        Follow.objects.create(user=self.author, author=self.follower)
        self.authorized_client.post(self.PROFILE_UNFOLLOW_URL)
        self.assertEqual(Follow.objects.count(), 0)

    def test_new_posts_on_page_followers(self):
        '''Новая запись пользователя появляется в ленте тех,
           кто на него подписан.
        '''
        Follow.objects.create(
            user=self.author,
            author=self.follower,
        )
        form_data = {
            "text": "test_text",
            "group": self.group.id,
            "author": self.follower,
        }
        self.follower_client.post(POST_CREATE_URL,
                                  data=form_data,
                                  follow=True,
                                  )
        first_post = Post.objects.first()
        response = self.authorized_client.get(FOLLOW_INDEX_URL)
        post = response.context['page_obj'][0]
        self.assertEqual(post, first_post)

    def test_new_post_not_show_on_page_unfollowers(self):
        '''Новая запись пользователя не появляется в ленте тех,
           кто НЕ подписан на него.
        '''
        Follow.objects.create(
            user=self.author,
            author=self.follower,
        )
        form_data = {
            "text": "test_text",
            "group": self.group.id,
            "author": self.follower,
        }
        self.follower_client.post(POST_CREATE_URL,
                                  data=form_data,
                                  follow=True,
                                  )
        response = self.follower_client.get(FOLLOW_INDEX_URL)
        posts = response.context['page_obj']
        self.assertEqual(len(posts), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='test_author')
        cls.group = Group.objects.create(title='test_title',
                                         slug='test_slug',
                                         description='test_discription')
        Post.objects.bulk_create(
            Post(author=cls.author, group=cls.group, text='test_post')
            for _ in range(POSTS_PER_PAGE)
        )
        cls.url_list = [
            INDEX_URL,
            GROUP_POSTS_URL,
            PROFILE_URL
        ]

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

    def test_paginator_of_first_page(self):
        '''Проверяется паджинатор вывода постов на первой странице.'''
        for url in self.url_list:
            response = self.guest_client.get(url)
            self.assertEqual(len(
                response.context['page_obj']),
                POSTS_PER_PAGE
            )
