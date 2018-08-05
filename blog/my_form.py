from django import forms
from django.forms import widgets
from django.core.exceptions import ValidationError

from blog.models import UserInfo


class RegisterForm(forms.Form):
    username = forms.CharField(
        label="用户名",
        min_length=4,
        max_length=32,
        error_messages={
            "required": "用户名不能为空",
            'min_length': "用户名长度不能小于4个字符",
            'max_length': "用户名长度不能大于32个字符"
        },
        widget=widgets.TextInput(attrs={"class": "form-control"})
    )
    password = forms.CharField(
        label="密码",
        max_length=32,
        min_length=6,
        error_messages={
            "required": "密码不能为空",
            'min_length': "密码长度不能小于6个字符",
            'max_length': "密码长度不能大于32个字符"
        },
        widget=widgets.PasswordInput(attrs={"class": "form-control"})
    )
    re_pwd = forms.CharField(
        label="确认密码",
        max_length=32,
        min_length=4,
        error_messages={
            "required": "密码不能为空",
            'min_length': "密码长度不能小于4个字符",
            'max_length': "密码长度不能大于32个字符"
        },
        widget=widgets.PasswordInput(attrs={"class": "form-control"})
    )
    email = forms.EmailField(
        max_length=32,
        label="邮箱",
        error_messages={
            "invalid": "邮箱格式错误",
            "required": "邮箱不能为空",
            'max_length': "邮箱长度不能大于32个字符"
        },
        widget=widgets.EmailInput(attrs={"class": "form-control"})
    )

    def clean_username(self):
        val = self.cleaned_data.get("username")

        username = UserInfo.objects.filter(username=val).first()
        if not username:
            return val
        else:
            raise ValidationError("该用户名已被注册!")

    def clean(self):
        password = self.cleaned_data.get("password")
        re_pwd = self.cleaned_data.get("re_pwd")

        if password and re_pwd:
            if password == re_pwd:
                return self.cleaned_data
            else:
                raise ValidationError("两次密码不一致!")
        else:
            return self.cleaned_data


class ArticleForm(forms.Form):
    title = forms.CharField(
        max_length=50,
        error_messages={
            "required": "标题不能为空",
            'max_length': "标题长度不能大于32个字符"
        }
    )
    content = forms.CharField(
        error_messages={
            "required": "文章内容不能为空",
        },
        widget=widgets.Textarea()
    )
