from django.shortcuts import render, HttpResponse, redirect
from django.contrib import auth
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from django.contrib.auth.decorators import login_required
from io import BytesIO
import json
import time
import os

from bs4 import BeautifulSoup
from blog.utils.check_code import create_validate_code
from blog.my_form import RegisterForm, ArticleForm
from blog import models
from pyblog import settings
from blog.utils.page import page


# Create your views here.


def login(request):
    if request.method == "POST":
        response = {"user": None, "msg": None}
        user = request.POST.get('user')
        pwd = request.POST.get('pwd')
        check_codes = request.POST.get('check_code')

        check_code_session = request.session.get('check_code')
        if check_codes.upper() == check_code_session.upper():
            user = auth.authenticate(username=user, password=pwd)
            if user:
                auth.login(request, user)
                response['user'] = user.username
            else:
                response['msg'] = '用户名或密码错误!'
        else:
            response['msg'] = '验证码错误!'
        return JsonResponse(response)
    return render(request, 'login.html')


def check_code(request):
    """图片验证码"""
    f = BytesIO()
    img, code = create_validate_code()
    request.session['check_code'] = code
    img.save(f, 'PNG')
    return HttpResponse(f.getvalue())


def logout(request):
    # 退出，清除session
    auth.logout(request)
    return redirect('/login/')


def index(request):
    article_list = models.Article.objects.all().order_by("-pk")
    page_range, current_page = page(article_list, request, 8)
    return render(request, 'index.html', locals())


def register(request):
    fm = RegisterForm()
    if request.is_ajax():
        fm = RegisterForm(request.POST)

        response = {"username": None, "msg": None}
        if fm.is_valid():
            username = fm.cleaned_data.get("username")
            password = fm.cleaned_data.get("password")
            email = fm.cleaned_data.get("email")
            avatar = request.FILES.get("avatar")
            response["username"] = username
            user_dict = {"username": username, "password": password, "email": email}
            if avatar:
                user_dict["avatar"] = avatar
            models.UserInfo.objects.create_user(**user_dict)
        else:
            response["msg"] = fm.errors
        return JsonResponse(response)
    return render(request, 'register.html', locals())


@login_required
def create_blog(request):
    """开通博客"""
    if request.method == "POST":
        site_name = request.POST.get("site_name")
        title = request.POST.get("title")
        response = '站点%s已存在，请重新输入' % site_name
        if not models.Blog.objects.filter(site_name=site_name):
            new_blog = models.Blog.objects.create(title=title, site_name=site_name)
            models.UserInfo.objects.filter(username=request.user.username).update(blog=new_blog)
            response = "OK"
        return HttpResponse(response)
    return render(request, 'create_blog.html')


def home(request, site, **kwargs):
    """
    个人主站,通过Blog下site_name访问
    """
    blog = models.Blog.objects.filter(site_name=site).first()
    if not blog:
        # return HttpResponse("NOT FOUND")
        return render(request, '404.html')
    user = blog.userinfo  # Blog反向查询Userinfo
    article_list = models.Article.objects.filter(user=user).order_by("-pk")

    if kwargs:
        condition = kwargs.get("condition")  # 初次筛选, 分类，tag|category|archive
        param = kwargs.get("param")  # 二次筛选，数据库查询
        if condition == "category":
            article_list = article_list.filter(category__title=param)
        elif condition == "tag":
            article_list = article_list.filter(tags__title=param)
        else:
            year, month = param.split("/")
            # 如果是mysql，修改settins.USE_TZ = False
            article_list = article_list.filter(create_time__year=year, create_time__month=month)


    return render(request, 'home.html', locals())


def article_detail(request, site, article_id):
    blog = models.Blog.objects.filter(site_name=site).first()
    if not blog:
        return HttpResponse("NOT FOUND")
    article = models.Article.objects.filter(pk=article_id).first()
    # 评论
    comment_list = models.Comment.objects.filter(article_id=article_id)

    return render(request, "article_detail.html", locals())


@login_required
def up_down(request):
    article_id = request.POST.get('article_id')
    is_up = json.loads(request.POST.get('is_up'))
    user_id = request.user.pk
    response = {'status': False, 'msg': '您已反对过'}
    obj = models.ArticleUpDown.objects.filter(user_id=user_id, article_id=article_id).first()
    if not obj:  # 没查到==没赞或踩过
        models.ArticleUpDown.objects.create(user_id=user_id, article_id=article_id, is_up=is_up)
        response["status"] = True
        if is_up:
            response["msg"] = "推荐成功"
            models.Article.objects.filter(pk=article_id).update(up_count=F("up_count") + 1)
        else:
            response["msg"] = "反对成功"
            models.Article.objects.filter(pk=article_id).update(down_count=F("down_count") + 1)
    elif obj.is_up:  # 已赞过
        response["msg"] = '您已推荐过'
    return HttpResponse(json.dumps(response))


@login_required
def comment(request):
    article_id = request.POST.get("article_id")
    pid = request.POST.get("pid")
    content = request.POST.get("content")
    user_id = request.user.pk

    # 事务操作
    with transaction.atomic():
        # 增加一条评论
        new_comment = models.Comment.objects.create(user_id=user_id, article_id=article_id, content=content,
                                                    parent_comment_id=pid)
        # 修改文章的评论数量
        models.Article.objects.filter(pk=article_id).update(comment_count=F("comment_count") + 1)

    response = {'new_comment_pk': new_comment.pk, 'time': time.strftime('%Y-%m-%d %H:%M')}

    return HttpResponse(json.dumps(response))


@login_required
def del_comment(request):
    comment_id = request.GET.get("comment_id")
    comment_obj = models.Comment.objects.filter(pk=comment_id)
    article_id = comment_obj.first().article_id
    # 该评论的子评论数量
    child_comment = models.Comment.objects.filter(parent_comment_id=comment_id).values_list('article_id')
    child_num = len(list(child_comment))
    del_num = child_num + 1
    comment_obj.delete()
    models.Article.objects.filter(pk=article_id).update(comment_count=F("comment_count") - del_num)

    return HttpResponse("OK")


def comment_tree(request):
    article_id = request.GET.get('article_id')
    response = list(models.Comment.objects.filter(article_id=article_id).
                    order_by("pk").values("pk", "content", "parent_comment_id"))
    return JsonResponse(response, safe=False)


@login_required
def backend(request):
    if not request.user.blog:
        return HttpResponse("您还未开通博客，暂时无法使用此功能！")
    article_list = models.Article.objects.filter(user_id=request.user.pk).order_by("-pk")

    return render(request, 'backend/backend.html', locals())


@login_required
def add_article(request, **kwargs):
    """添加或编辑文章"""
    fm = ArticleForm()
    tags = models.Tag.objects.filter(blog=request.user.blog)
    categories = models.Category.objects.filter(blog=request.user.blog)
    if kwargs:  # 编辑文章
        article_obj = models.Article.objects.filter(pk=kwargs["article_id"]).first()
        article_tags = models.Article2Tag.objects.filter(article=article_obj)
        article_tags_list = []
        for i in article_tags:
            article_tags_list.append(i.tag_id)
    if request.method == "POST":
        fm = ArticleForm(request.POST)
        if fm.is_valid():
            title = request.POST.get("title")
            content = request.POST.get("content")
            tag_id_list = request.POST.getlist("tag_id_list")
            category_id = request.POST.get("category_id")

            # 防止XSS攻击，过滤指定的html标签
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup.find_all():
                if tag.name == "script":
                    tag.decompose()    # 删除html标签

            desc = soup.text[0: 150] + '...'
            if category_id == '0':
                category_id = None
            if kwargs:  # 修改，包括分类
                models.Article.objects.filter(pk=kwargs["article_id"]).\
                    update(title=title, desc=desc, content=str(soup), user=request.user, category_id=category_id)
                if tag_id_list:  # 修改tag
                    models.Article2Tag.objects.filter(article_id=kwargs["article_id"]).delete()
                    for i in tag_id_list:
                        models.Article2Tag.objects.create(article_id=kwargs["article_id"], tag_id=int(i))
            else:  # 创建
                new_article = models.Article.objects.\
                    create(title=title, desc=desc, content=str(soup), user=request.user, category_id=category_id)
                if tag_id_list:
                    for i in tag_id_list:
                        models.Article2Tag.objects.create(article=new_article, tag_id=int(i))

            return redirect('/backend/')
        else:
            return render(request, 'backend/add_article.html', locals())

    return render(request, 'backend/add_article.html', locals())


@login_required
def delete_article(request):
    article_id = request.GET.get("article_id")
    models.Article.objects.filter(pk=article_id).delete()

    return HttpResponse("OK")


@login_required
def add_tag(request):
    to = request.GET.get("to")
    if request.method == "POST":
        title = request.POST.get("title")
        to = request.POST.get('to')
        response = {"to": to, 'msg': "标签已存在"}
        if not models.Tag.objects.filter(title=title, blog=request.user.blog):
            models.Tag.objects.create(title=title, blog=request.user.blog)
            response['msg'] = ''
        return JsonResponse(response)
    return render(request, 'backend/add_tag.html', locals())


@login_required
def add_category(request):
    to = request.GET.get("to")
    if request.method == "POST":
        title = request.POST.get("title")
        to = request.POST.get('to')
        response = {"to": to, 'msg': "标签已存在"}
        if not models.Category.objects.filter(title=title, blog=request.user.blog):
            models.Category.objects.create(title=title, blog=request.user.blog)
            response['msg'] = ''
        return JsonResponse(response)
    return render(request, 'backend/add_category.html', locals())


@login_required
def upload(request):

    img_obj = request.FILES.get("upload_img")

    path = os.path.join(settings.MEDIA_ROOT, "add_article_img", img_obj.name)

    with open(path, "wb") as f:
        for line in img_obj:
            f.write(line)

    response = {   # 设置上传的图片直接显示在输入框内
        "error": 0,
        "url": os.path.join(settings.MEDIA_URL, 'add_article_img', img_obj.name)
    }

    return HttpResponse(json.dumps(response))
