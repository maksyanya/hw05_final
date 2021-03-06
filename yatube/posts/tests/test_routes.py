from django.test import TestCase
from django.urls import reverse


USERNAME = 'test_author'
SLUG = 'test_slug'
ID = 1


class PostRoutesTests(TestCase):
    def test_urls_correct_use(self):
        '''Проверяется маршруты явных и рассчётных урлов.'''
        url_list = [
            ['/', 'index', []],
            ['/create/', 'post_create', []],
            [f'/group/{SLUG}/', 'group_posts', [SLUG]],
            [f'/posts/{ID}/', 'post_detail', [ID]],
            [f'/profile/{USERNAME}/', 'profile', [USERNAME]],
            [f'/posts/{ID}/edit/', 'post_edit', [ID]],
            [f'/posts/{ID}/comment/', 'add_comment', [ID]],
            ['/follow/', 'follow_index', []],
            [f'/profile/{USERNAME}/follow/', 'profile_follow', [USERNAME]],
            [f'/profile/{USERNAME}/unfollow/', 'profile_unfollow', [USERNAME]]
        ]
        for url, name, parametr in url_list:
            self.assertEqual(url, reverse(f'posts:{name}', args=parametr))
