
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page

from posts.forms import CommentForm
from posts.forms import PostForm
from posts.models import Follow
from posts.models import Group
from posts.models import Post
from posts.models import User
from posts.settings import POSTS_PER_PAGE


def get_page(request, posts):
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


@cache_page(20)
def index(request):
    return render(request, 'posts/index.html', context={
        'page_obj': get_page(request, Post.objects.all()),
    })


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    return render(request, 'posts/group_list.html', context={
        'page_obj': get_page(request, group.posts.all()),
        'group': group,
    })


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    page_obj = get_page(request, posts)
    if (request.user.is_authenticated
        and Follow.objects.filter(
            user=request.user,
            author=author).exists()):
        following = True
    else:
        following = False
    context = {
        'page_obj': page_obj,
        'author': author,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.select_related('author')
    context = {
        'post': post,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', username=post.author.username)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect(
            'posts:post_detail',
            post_id=post.id
        )
    form = PostForm(
        request.POST or None,
        request.FILES or None,
        instance=post)
    if not form.is_valid():
        context = {
            'post': post,
            'form': form,
            'is_edit': True
        }
        return render(request, 'posts/create_post.html', context)
    form.save()
    return redirect(
        'posts:post_detail',
        post_id=post.id
    )


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post.id)


@login_required
def follow_index(request):
    followings = Follow.objects.filter(
        user=request.user).values_list('author')
    post_list = Post.objects.filter(author_id__in=followings)
    return render(request, 'posts/follow.html', context={
        'page_obj': get_page(request, post_list)
    })


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if (
        author == request.user
        or Follow.objects.filter(author=author, user=request.user).exists()
    ):
        return redirect('posts:profile', username=username)
    Follow.objects.create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    follow_check = Follow.objects.filter(user=request.user, author=author)
    if follow_check:
        Follow.objects.filter(user=request.user, author=author).exists()
        follow_check.delete()
    return redirect('posts:profile', username=username)
