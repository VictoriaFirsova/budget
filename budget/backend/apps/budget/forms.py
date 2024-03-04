from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Category


class UploadFileForm(forms.Form):
    """Форма для загрузки файла."""

    file = forms.FileField(label="Файл")


class RegistrationForm(UserCreationForm):
    """Форма для регистрации пользователя."""

    email = forms.EmailField(
        max_length=254, help_text="Required. Enter a valid email address."
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class StatementFilterForm(forms.Form):
    """Форма для фильтрации заявок."""

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Выбор категории",
        required=False,
        label="Категория",
    )


class ChangeCategoryForm(forms.Form):
    """Форма для изменения категории"""

    statement_id = forms.IntegerField(widget=forms.HiddenInput())
    new_category = forms.ModelChoiceField(
        queryset=Category.objects.all(), empty_label=None
    )
