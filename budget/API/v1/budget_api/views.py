from rest_framework import viewsets
from .serializers import StatementSerializer, CategorySerializer
from budget.budget.models import Statement, Category


class StatementViewSet(viewsets.ModelViewSet):
    queryset = Statement.objects.all()
    serializer_class = StatementSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
