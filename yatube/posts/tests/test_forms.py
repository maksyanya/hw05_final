import shutil
import tempfile
from copy import copy

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from django import forms
from posts.models import Comment
from posts.models import Group
from posts.models import Post
from posts.models import User


USERNAME = 'test_author'
TITLE = 'test_group'
SLUG = 'test_slug'
DESCRIPTION = 'test_description'
TITLE_NEW = 'test_group_new'
SLUG_NEW = 'test_slug_new'
DESCRIPTION_NEW = 'test_description_new'
SMALL_GIF = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B')

PROFILE_URL = reverse('posts:profile', kwargs={'username': USERNAME})
POST_CREATE_URL = reverse('posts:post_create')
LOGIN = reverse('login')

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username=USERNAME)
        cls.group = Group.objects.create(
            title=TITLE,
            slug=SLUG,
            description=DESCRIPTION
        )
        cls.group_new = Group.objects.create(
            title=TITLE_NEW,
            slug=SLUG_NEW,
            description=DESCRIPTION_NEW
        )

        cls.post = Post.objects.create(author=cls.user,
                                       group=cls.group,
                                       text='test_text',
                                       )
        cls.comment = Comment.objects.create(post=cls.post,
                                             author=cls.user,
                                             text='test_comment')

        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.id])
        cls.POST_COMMENT_URL = reverse('posts:add_comment', args=[cls.post.id])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.editor = User.objects.create(username='not_author')
        self.editor_client = Client()
        self.editor_client.force_login(self.editor)
        self.image = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )

    def test_form_create(self):
        '''Проверяется создания нового поста авторизированным пользователем.'''
        post_count = Post.objects.count()
        form_data = {
            'text': 'test_text',
            'group': self.group.id,
            'image': self.image
        }
        response = self.authorized_client.post(POST_CREATE_URL,
                                               data=form_data,
                                               follow=True)
        self.assertRedirects(response, PROFILE_URL)
        post = Post.objects.first()
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.text, form_data['text'])
        self.assertTrue(post.image)

    def test_edit_post(self):
        '''Проверяется редактирование поста через форму на странице.'''
        form_data_new = {
            'text': 'edited_text',
            'group': self.group_new.id,
            'image': self.image
        }
        response = self.authorized_client.post(self.POST_EDIT_URL,
                                               data=form_data_new,
                                               follow=True)
        post_edit = Post.objects.first()
        self.assertRedirects(response, self.POST_DETAIL_URL)
        self.assertEqual(post_edit.group.id, form_data_new['group'])
        self.assertEqual(post_edit.text, form_data_new['text'])
        self.assertEqual(post_edit.author, self.user)
        self.assertEqual(post_edit.image, 'posts/small.gif')

    def test_post_create_and_edit_page_show_correct_context(self):
        '''Проверяется добавление/редактирование записи
        с правильным контекстом.'''
        self.url_list = [POST_CREATE_URL, self.POST_EDIT_URL]
        for url in self.url_list:
            response = self.authorized_client.get(url)
            form_fields = {
                'group': forms.fields.ChoiceField,
                'text': forms.fields.CharField,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_fields = response.context['form'].fields[value]
                    self.assertIsInstance(form_fields, expected)

    def test_add_comments_authorized_user(self):
        '''Проверяется комментирование постов
           авторизированным пользователем.
        '''
        form_data = {'text': 'test_comment', 'author': self.user}
        response = self.authorized_client.post(self.POST_COMMENT_URL,
                                               data=form_data,
                                               follow=True)
        self.assertRedirects(response, self.POST_DETAIL_URL)
        comment = Comment.objects.first()
        self.assertEqual(comment.author, form_data['author'])
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.text, form_data['text'])

    def test_create_post_by_guest(self):
        '''Проверяется, что аноним не может создать пост.'''
        old_post = copy(self.post)
        form_data = {'text': 'guest client can not create post'}
        response = self.guest_client.post(POST_CREATE_URL,
                                          data=form_data,
                                          follow=True)
        self.assertRedirects(response, (LOGIN + '?next=' + POST_CREATE_URL))
        self.assertEqual(Post.objects.count(), 1)
        self.post.refresh_from_db()
        self.assertEqual(old_post.text, self.post.text)
        self.assertEqual(old_post.author, self.post.author)

    def test_add_comment_by_guest(self):
        '''Проверяется, что аноним не может добавить комментарий.'''
        comments_count = Comment.objects.count()
        form_data = {'text': 'test_comment'}
        response = self.guest_client.post(self.POST_COMMENT_URL,
                                          data=form_data,
                                          follow=True,)
        self.assertRedirects(response,
                             (LOGIN + '?next=' + self.POST_COMMENT_URL))
        self.assertEqual(comments_count, Comment.objects.count())

    def test_edit_post_by_guest(self):
        '''Проверяется, что аноним не может редактировать пост.'''
        old = copy(self.post)
        form_data = {
            'group': self.group.id,
            'text': 'guest client can not edit post'
        }
        response = self.guest_client.post(self.POST_EDIT_URL,
                                          data=form_data,
                                          follow=True)
        self.assertRedirects(response,
                             LOGIN + '?next=' + self.POST_EDIT_URL)
        self.post.refresh_from_db()
        self.assertEqual(self.post.text, old.text)
        self.assertEqual(self.post.group, old.group)

    def test_edit_post_not_author(self):
        '''Проверяется, что не автор не может редактировать пост.'''
        old = copy(self.post)
        form_data = {
            'group': self.group.id,
            'author': self.editor,
            'text': self.post.text
        }
        response = self.editor_client.post(self.POST_EDIT_URL,
                                           data=form_data,
                                           follow=True)
        self.assertRedirects(response, self.POST_DETAIL_URL)
        self.post.refresh_from_db()
        self.assertEqual(self.post.text, old.text)
        self.assertEqual(self.post.group, old.group)
        self.assertEqual(self.post.author, old.author)
