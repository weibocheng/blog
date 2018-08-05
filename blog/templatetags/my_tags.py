from django.db.models import Count
from django import template
from blog import models

register = template.Library()

# 自定义模板标签，文件夹名字必须是templatetags，文件名随意


@register.inclusion_tag('left_menu.html')
def left_menu(site):
    """
    执行以下查询操作之后，把数据返回给inclusion_tag，
    渲染left_menu.html这个模板文件
    调用时：{% load my_tags %}
            {% left_menu site %}
    """
    blog = models.Blog.objects.filter(site_name=site).first()
    user = blog.userinfo  # Blog反向查询Userinfo
    print('user??', user)
    tag_list = models.Tag.objects.filter(blog=blog).values("pk").annotate(c=Count("article")).values_list("title", "c")
    #                                               任意字段         聚合
    cate_list = models.Category.objects.filter(blog=blog).values("pk"). \
        annotate(c=Count("article__title")).values_list("title", "c")
    date_list = models.Article.objects.filter(user=user). \
        extra(select={"y_m_date": "strftime('%%Y/%%m', create_time)"}).values("y_m_date").annotate(c=Count("nid")). \
        values_list("y_m_date", "c").order_by("-y_m_date")
    return {"blog": blog, "cate_list": cate_list, "date_list": date_list, "tag_list": tag_list}
