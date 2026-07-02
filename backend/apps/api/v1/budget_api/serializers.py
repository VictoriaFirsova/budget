from typing import Any

from rest_framework import serializers
from apps.budget.models import Category, ImportTemplate, Statement


class StatementSerializer(serializers.ModelSerializer):
    my_category_title = serializers.CharField(
        source="my_category.title", read_only=True
    )

    class Meta:
        model = Statement
        fields = "__all__"
        read_only_fields = ("user",)

    def validate_my_category(self, value):
        request = self.context.get("request")
        if (
            value
            and request
            and request.user.is_authenticated
            and value.user_id != request.user.id
        ):
            raise serializers.ValidationError(
                "Category does not belong to current user."
            )
        return value


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ("user",)
        validators: list[Any] = []

    def validate_title(self, value):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            queryset = Category.objects.filter(user=request.user, title=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    "Category with this title already exists."
                )
        return value


class ImportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportTemplate
        fields = "__all__"
        read_only_fields = ("user", "created_at", "updated_at")
        validators: list[Any] = []

    def validate_name(self, value):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            queryset = ImportTemplate.objects.filter(user=request.user, name=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    "Import template with this name already exists."
                )
        return value
