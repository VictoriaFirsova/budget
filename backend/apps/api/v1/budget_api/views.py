import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import (
    authenticate,
    login as django_login,
    logout as django_logout,
)
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework.authentication import SessionAuthentication
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.budget.importers import (
    StatementImportError,
    import_statements_from_rows,
    import_statements_from_file,
    preview_statements_from_file,
)
from apps.budget.models import Category, ImportTemplate, Statement
from .serializers import (
    CategorySerializer,
    ImportTemplateSerializer,
    StatementSerializer,
)


def _serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }


def _format_decimal(value):
    return str(value.quantize(Decimal("0.01")))


def _add_amount(bucket, currency, amount):
    bucket[currency] += amount


def _resolve_analytics_period(params):
    period = params.get("period", "month")
    today = date.today()

    if period == "week":
        return period, today - timedelta(days=6), today
    if period == "month":
        return period, today.replace(day=1), today
    if period == "year":
        return period, today.replace(month=1, day=1), today
    if period == "custom":
        date_from = parse_date(params.get("date_from") or "")
        date_to = parse_date(params.get("date_to") or "")
        if not date_from or not date_to:
            raise ValueError("date_from and date_to are required for custom period.")
        if date_from > date_to:
            raise ValueError("date_from cannot be later than date_to.")
        return period, date_from, date_to

    raise ValueError("Unsupported period.")


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


class StatementViewSet(viewsets.ModelViewSet):
    serializer_class = StatementSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = Statement.objects.filter(user=self.request.user)
        params = self.request.query_params

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(operation_name__icontains=search)
                | Q(category__icontains=search)
                | Q(my_category__title__icontains=search)
                | Q(card__icontains=search)
                | Q(currency__icontains=search)
            )

        category_id = params.get("category")
        if category_id:
            queryset = queryset.filter(my_category_id=category_id)

        currency = params.get("currency")
        if currency:
            queryset = queryset.filter(currency__iexact=currency)

        card = params.get("card")
        if card:
            queryset = queryset.filter(card__icontains=card)

        date_from = params.get("date_from")
        if date_from:
            queryset = queryset.filter(date__gte=date_from)

        date_to = params.get("date_to")
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset.order_by("-date", "-id")


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).order_by("title")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ImportTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ImportTemplateSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ImportTemplate.objects.filter(user=self.request.user).order_by("name")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BudgetAnalyticsView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            period, date_from, date_to = _resolve_analytics_period(request.query_params)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        statements = Statement.objects.filter(
            user=request.user,
            date__gte=date_from,
            date__lte=date_to,
        ).select_related("my_category")

        income_by_currency = defaultdict(Decimal)
        expense_by_currency = defaultdict(Decimal)
        category_expenses = defaultdict(Decimal)
        timeline = defaultdict(
            lambda: {"income": defaultdict(Decimal), "expense": defaultdict(Decimal)}
        )
        expense_count = 0
        income_count = 0

        timeline_granularity = "month" if period == "year" else "day"

        for statement in statements:
            currency = statement.currency
            amount = statement.amount
            if timeline_granularity == "month":
                bucket_date = statement.date.replace(day=1).isoformat()
            else:
                bucket_date = statement.date.isoformat()

            if amount < 0:
                expense_amount = abs(amount)
                _add_amount(expense_by_currency, currency, expense_amount)
                category_title = (
                    statement.my_category.title
                    if statement.my_category
                    else "Без категории"
                )
                category_expenses[(category_title, currency)] += expense_amount
                timeline[bucket_date]["expense"][currency] += expense_amount
                expense_count += 1
            elif amount > 0:
                _add_amount(income_by_currency, currency, amount)
                timeline[bucket_date]["income"][currency] += amount
                income_count += 1

        currencies = sorted(set(income_by_currency) | set(expense_by_currency))
        summary = [
            {
                "currency": currency,
                "income": _format_decimal(income_by_currency[currency]),
                "expense": _format_decimal(expense_by_currency[currency]),
                "balance": _format_decimal(
                    income_by_currency[currency] - expense_by_currency[currency]
                ),
            }
            for currency in currencies
        ]

        category_rows = [
            {
                "category": category,
                "currency": currency,
                "amount": _format_decimal(amount),
            }
            for (category, currency), amount in category_expenses.items()
        ]
        category_rows.sort(key=lambda row: (row["currency"], -Decimal(row["amount"])))

        timeline_rows = []
        for bucket_date in sorted(timeline):
            bucket = timeline[bucket_date]
            bucket_currencies = sorted(set(bucket["income"]) | set(bucket["expense"]))
            for currency in bucket_currencies:
                timeline_rows.append(
                    {
                        "date": bucket_date,
                        "currency": currency,
                        "income": _format_decimal(bucket["income"][currency]),
                        "expense": _format_decimal(bucket["expense"][currency]),
                        "balance": _format_decimal(
                            bucket["income"][currency] - bucket["expense"][currency]
                        ),
                    }
                )

        return Response(
            {
                "period": period,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "timeline_granularity": timeline_granularity,
                "summary": summary,
                "category_expenses": category_rows,
                "top_expenses": category_rows[:8],
                "timeline": timeline_rows,
                "counts": {
                    "total": statements.count(),
                    "income": income_count,
                    "expense": expense_count,
                },
            }
        )


class LoginView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        django_login(request, user)
        return Response({"user": _serialize_user(user)})


class RegisterView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", "")

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": "User with this username already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        django_login(request, user)
        return Response({"user": _serialize_user(user)}, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request):
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StatementImportView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response(
                {"detail": "File is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        schema_payload = request.data.get("schema")
        if not schema_payload:
            return Response(
                {"detail": "Column schema is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            schema = json.loads(schema_payload)
        except json.JSONDecodeError:
            return Response(
                {"detail": "Column schema must be valid JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_statements_from_file(uploaded_file, schema, request.user)
        except StatementImportError as exc:
            return Response(
                {"detail": str(exc), "errors": exc.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "created": result.created,
                "skipped_duplicates": result.skipped_duplicates,
                "skipped_invalid": result.skipped_invalid,
                "errors": result.errors,
            },
            status=status.HTTP_201_CREATED,
        )


class StatementImportPreviewView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response(
                {"detail": "File is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        schema_payload = request.data.get("schema")
        if not schema_payload:
            return Response(
                {"detail": "Column schema is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            schema = json.loads(schema_payload)
        except json.JSONDecodeError:
            return Response(
                {"detail": "Column schema must be valid JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = preview_statements_from_file(uploaded_file, schema, request.user)
        except StatementImportError as exc:
            return Response(
                {"detail": str(exc), "errors": exc.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "rows": result.rows,
                "skipped_invalid": result.skipped_invalid,
                "errors": result.errors,
            }
        )


class StatementManualImportView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        rows = request.data.get("rows")
        if not isinstance(rows, list):
            return Response(
                {"detail": "Rows must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = import_statements_from_rows(rows, request.user)
        except StatementImportError as exc:
            return Response(
                {"detail": str(exc), "errors": exc.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "created": result.created,
                "skipped_duplicates": result.skipped_duplicates,
                "skipped_invalid": result.skipped_invalid,
                "errors": result.errors,
            },
            status=status.HTTP_201_CREATED,
        )
