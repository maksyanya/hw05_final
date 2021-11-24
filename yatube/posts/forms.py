from django.db.models import fields
from django.forms import ModelForm
from posts.models import Comment
from posts.models import Post


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': 'Текст поста',
            'group': 'Сообщество'}
        help_text = {
            'text': 'Hапишите свой пост здесь',
            'group': 'Выберите сообщество'}

class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)