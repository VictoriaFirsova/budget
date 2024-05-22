from datetime import date
from decimal import Decimal
import pytest
from backend.apps.budget.models import Category, Statement


@pytest.mark.django_db
def test_category_creation():
    Category.objects.create(title="Test")
    assert Category.objects.count() == 1


@pytest.mark.django_db
def test_statement_creation():
    statement = Statement.objects.create(
        date=date(2024, 4, 11),
        operation_name="Test operation",
        amount=Decimal('100.00'),
        currency="USD",
        category="Test category"
    )
    assert Statement.objects.count() == 1
    assert statement.operation_name == "Test operation"
    assert statement.amount == Decimal('100.00')
    assert statement.currency == "USD"
    assert statement.category == "Test category"


@pytest.mark.django_db
def test_statement_str_method():
    statement = Statement.objects.create(
        date=date(2024, 4, 11),
        amount=Decimal('100.00')
    )
    assert str(statement) == "2024-04-11 100.00"