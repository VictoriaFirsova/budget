import io
import requests
import pandas as pd
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.db.models import Sum
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic.edit import FormView
from datetime import datetime, timedelta
import mimetypes
import chardet
from .forms import (
    UploadFileForm,
    RegistrationForm,
    StatementFilterForm,
    ChangeCategoryForm,
)
from .models import Statement, Category
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from urllib.parse import urlencode


def create_paginator(queryset, items_per_page, page_number, request_params):
    # Создаем пагинатор
    paginator = Paginator(queryset, items_per_page)
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    # Сохраняем параметры фильтрации в ссылках пагинатора
    page.object_list.request_params = request_params
    return paginator, page


def home(request):
    # Отображение записей из базы данных на главное странице
    statements_list = Statement.objects.all().order_by("date")

    # Добавляем обработку фильтров по времени
    time_filter = request.GET.get("time_filter")
    if time_filter:
        today = datetime.now()
        if time_filter == "last_month":
            start_date = today - timedelta(days=30)
            end_date = today
            statements_list = statements_list.filter(date__range=[start_date, end_date])
        elif time_filter == "last_quarter":
            start_date = today - timedelta(days=90)
            end_date = today
            statements_list = statements_list.filter(date__range=[start_date, end_date])
        elif time_filter == "last_half_year":
            start_date = today - timedelta(days=180)
            end_date = today
            statements_list = statements_list.filter(date__range=[start_date, end_date])
        elif time_filter == "last_year":
            start_date = today - timedelta(days=365)
            end_date = today
            statements_list = statements_list.filter(date__range=[start_date, end_date])
        else:
            start_date = request.GET.get("start_date")
            end_date = request.GET.get("end_date")
            if start_date and end_date:
                statements_list = statements_list.filter(
                    date__range=[start_date, end_date]
                )

    # Применяем фильтр по категории к исходному queryset перед пагинацией
    selected_category = request.GET.get("category")
    if selected_category:
        statements_list = statements_list.filter(my_category=selected_category)
    # Запоминаем параметры фильтрации для использования в пагинаторе
    request_params = request.GET.copy()
    paginator, statements = create_paginator(
        statements_list, 10, request.GET.get("page", 1), urlencode(request_params)
    )
    total_amount = statements_list.aggregate(Sum("amount"))["amount__sum"]

    # Добавляем обработку фильтров по карте
    card_filter = request.GET.get("card_filter")
    if card_filter:
        if card_filter == "TBC":
            statements_list = statements_list.filter(operation_name__contains="TBC")
        elif card_filter == "Priorbank":
            statements_list = statements_list.filter(
                operation_name__contains="Priorbank"
            )
        else:
            statements_list = Statement.objects.all().order_by("date")

    if request.method == "POST":
        change_category_form = ChangeCategoryForm(request.POST)
        if change_category_form.is_valid():
            statement_id = change_category_form.cleaned_data.get("statement_id")
            new_category = change_category_form.cleaned_data.get("new_category")

            statement = Statement.objects.get(id=statement_id)
            statement.my_category = new_category
            statement.save()

            return redirect("home")

    else:
        selected_currency = request.GET.get("currency")
        if selected_currency:
            statements_list = statements_list.filter(currency=selected_currency)
            total_amount = statements_list.aggregate(Sum("amount"))["amount__sum"]

        filter_form = StatementFilterForm(request.GET)
        if filter_form.is_valid():
            selected_category = filter_form.cleaned_data.get("category")
            if selected_category:
                statements_list = statements_list.filter(my_category=selected_category)
                total_amount = statements_list.aggregate(Sum("amount"))["amount__sum"]
        # Запоминаем параметры фильтрации для использования в пагинаторе
        request_params = request.GET.copy()
        # Создаем новый пагинатор после применения фильтров
        paginator_filtered, statements_filtered = create_paginator(
            statements_list, 10, request.GET.get("page", 1), urlencode(request_params)
        )

        change_category_forms = [
            ChangeCategoryForm(initial={"statement_id": statement.id})
            for statement in statements
        ]
        # Переопределяем ссылки пагинатора с учетом параметров фильтрации
        page_range = [
            f"?{urlencode(request_params)}&page={page}"
            for page in paginator_filtered.page_range
        ]

        return render(
            request,
            "home.html",
            {
                "statements": zip(statements_filtered, change_category_forms),
                "total_amount": total_amount,
                "filter_form": filter_form,
                "paginator": paginator_filtered,
                "page_range": page_range,
            },
        )


def logout(request):
    if request.user.is_authenticated:
        auth_logout(request)
        return render(request, "home.html")


def login(request):
    # логирование пользователя
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect("home")
        else:
            return render(
                request, "login.html", {"error_message": "Invalid login credentials"}
            )

    return render(request, "registration/login.html")


def registration_view(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect("home")
    else:
        form = RegistrationForm()

    return render(request, "registration/registration.html", {"form": form})


def drop(request):
    return render(request, "drop.html")


# получение данных из бд
def categories_list(request):
    categories = Category.objects.all().order_by("title")
    return render(request, "categories_list.html", {"categories": categories})


def statements_list(request):
    statements = Statement.objects.order_by("date").all()[:10]
    return render(request, "home.html", {"statements": statements})


# сохранение данных в бд
def create(request):
    if request.method == "POST":
        tom = Category()
        tom.title = request.POST.get("title")
        tom.save()
    return HttpResponseRedirect("/categories_list")


# изменение данных в бд
def edit(request, id):
    try:
        category = Category.objects.get(id=id)

        if request.method == "POST":
            category.title = request.POST.get("title")
            category.save()
            return HttpResponseRedirect("/categories_list")
        else:
            return render(request, "edit.html", {"category": category})
    except Category.DoesNotExist:
        return HttpResponseNotFound("<h2>Category not found</h2>")


# удаление данных из бд
def delete(request, id):
    try:
        category = Category.objects.get(id=id)
        category.delete()
        return HttpResponseRedirect("/categories_list")
    except Category.DoesNotExist:
        return HttpResponseNotFound("<h2>Category not found</h2>")


class UploadPaymentFileView(FormView):
    # Определяем класс формы
    form_class = UploadFileForm
    template_name = "drop.html"

    def post(self, request, **kwargs):
        # Обработка загруженного файла
        try:
            uploaded_file = request.FILES["file"]
            if "file" not in request.FILES:
                messages.error(request, "Необходимо выбрать файл для загрузки.")
                return render(request, self.template_name, {"form": self.form_class()})
            mime_type, encoding = mimetypes.guess_type(uploaded_file.name)

            if not mime_type or mime_type not in (
                "text/csv",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ):
                messages.error(
                    request,
                    "Недопустимый формат файла. Пожалуйста, загрузите файл формата CSV или XLSX.",
                )
                return render(request, self.template_name, {"form": self.form_class()})
            # Определение кодировки файла с использованием chardet

            detector = chardet.universaldetector.UniversalDetector()
            for line in uploaded_file:
                detector.feed(line)
                if detector.done:
                    break
            detector.close()

            # Получение предполагаемой кодировки
            detected_encoding = detector.result["encoding"]
            # Если chardet не смог определить кодировку, используйте кодировку по умолчанию (например, utf-8)
            if detected_encoding is None:
                detected_encoding = "utf-8"

            uploaded_file.seek(0)
            csv_content = uploaded_file.read().decode(
                detected_encoding, errors="replace"
            )
            detected_encoding = self.detecting_encoding(csv_content)
            card_type = self.determine_card_type(uploaded_file)
            uploaded_file.seek(0)
            self.save_statement(
                self.change_rate(
                    self.read_csv_content(csv_content, detected_encoding, card_type)
                )
            )

            uploaded_file.seek(0)

            return redirect(reverse("home"))
        except Exception as e:
            # Выводим информацию об ошибке
            print(f"An error occurred: {e}")
            return HttpResponse(status=500)  # Возвращаем HTTP 500 в случае ошибки

    def determine_card_type(self, uploaded_file):
        # Определение типа карты по имени файла
        if uploaded_file.name.startswith("account_statement"):
            card_type = "TBC Bank"
            return card_type
        elif uploaded_file.name.startswith("Vpsk"):
            card_type = "Priorbank"
            return card_type
        else:
            card_type = "Unknown"
            return card_type

    def detecting_encoding(self, csv_content):
        # Определение кодировки файла с использованием chardet
        detector = chardet.universaldetector.UniversalDetector()
        detector.feed(csv_content.encode())
        detector.close()

        # Получение предполагаемой кодировки
        detected_encoding = detector.result["encoding"]
        # Если chardet не смог определить кодировку, используйте кодировку по умолчанию (например, utf-8)
        if detected_encoding is None:
            detected_encoding = "utf-8"
        return detected_encoding

    def read_csv_content(self, csv_content, detected_encoding, card_type):
        if card_type == "Priorbank":
            # разбор выписки в формате csv в датафрэйм
            io_data = io.BytesIO(csv_content.encode(detected_encoding))
            try:
                df = pd.read_csv(
                    io_data,
                    index_col=False,
                    delimiter=";",
                    skiprows=25,
                    # nrows=1,  # убрать после отладки
                    encoding=detected_encoding,
                    names=[
                        "date",
                        "operation_name",
                        "amount",
                        "currency",
                        "dateop",
                        "com",
                        "ob",
                        "card",
                        "category",
                    ],
                )
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            except ValueError as e:
                # Обработка ошибки, например, вывод сообщения в лог
                print(f"Error processing dateop column: {e}")

                df = pd.DataFrame()
            df = df.dropna(subset=["date"])
            df.drop(["dateop", "com", "ob", "card"], inplace=True, axis=1)
            df["amount"] = df["amount"].str.replace(",", ".")
            df["amount"] = df["amount"].str.replace(" ", "")
            df["amount"] = pd.to_numeric(df["amount"])
            df["amount"] = df["amount"].apply(lambda x: x * -1)
            df["date"] = pd.to_datetime(df["date"], dayfirst=True)
            df["date"] = df["date"].dt.date
            df = df.query("~(amount >= 0)")

        elif card_type == "TBC Bank":
            # разбор выписки в формате csv в датафрэйм
            mcc_data = pd.read_excel(
                "mcc.xls", header=None, index_col=0, names=["descr"]
            )
            mcc_stock = pd.DataFrame(
                mcc_data,
            )
            io_data = io.BytesIO(csv_content.encode(detected_encoding))
            data = pd.read_csv(
                io_data,
                delimiter=",",
                skiprows=1,
                parse_dates=True,
            )  # убрать после отладки nrows=5,
            df = pd.DataFrame(data)
            df.columns = df.columns.str.replace("Description", "operation_name")
            df.columns = df.columns.str.replace("Date", "date")
            df.columns = df.columns.str.replace("Paid Out", "amount")
            df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
            df["date"] = df["date"].dt.date
            df = df.iloc[:, [0, 1, 3]]
            df = df.dropna()
            for i in df.iterrows():
                df.loc[i[0], "currency"] = "USD"
                df.loc[i[0], "category"] = "Другое"

                type_desc = i[1].iloc[1]
                if type_desc == "კონვერტაცია":
                    df.loc[i[0], "category"] = "conversion"
                try:
                    num = type_desc.index("MCC")
                    type_op = int(type_desc[(num + 5) : (num + 9)])

                    if (
                        df.loc[i[0], "category"] == "Другое"
                        or df.loc[i[0], "category"] == "nan"
                    ):
                        try:
                            mcc_category = mcc_stock.loc[type_op]
                            df.loc[i[0], "category"] = mcc_category["descr"]
                        except BaseException as e:
                            print(e)
                            continue
                except:
                    continue

        return df

    def change_rate(self, df):
        # Преобразование суммы, если валюта не USD
        for index, row in df.iterrows():
            amount = row["amount"]
            date = row["date"]
            currency = row["currency"]

            if currency != "USD":
                try:
                    url = (
                        f"http://api.currencylayer.com/historical"
                        f"?access_key=08a52bdae380b4f4534306be6bd40dec"
                        f"&date={date}"
                        f"&source={currency}"
                        f"&currencies=USD"
                        f"&format=1"
                    )
                    response = requests.request("GET", url)
                    # Парсим JSON-ответ
                    exchange_rates = response.json().get("quotes", {})

                    # Извлекаем курс для USD
                    usd_rate = exchange_rates.get(f"{currency}USD", 1.0)

                    # умножаем сумму на курс
                    df.at[index, "amount"] = amount * usd_rate
                    df.at[index, "currency"] = "USD"

                except Exception as e:
                    # Выводим информацию об ошибке
                    print(f"An error occurred: {e}")
        return df

    def save_statement(self, df):
        # Сохранение датафрэйма в базу данных
        for index, column in df.iterrows():
            if not Statement.objects.filter(
                date=column["date"],
                operation_name=column["operation_name"],
                amount=column["amount"],
                currency=column["currency"],
                category=column["category"],
            ).exists():
                my_category = self.get_category(column["category"])
                Statement.objects.create(
                    date=column["date"],
                    operation_name=column["operation_name"],
                    amount=column["amount"],
                    currency=column["currency"],
                    category=column["category"],
                    my_category=my_category,
                )

    def get_category(self, category_name):
        # Словарь, связывающий имена категорий из ваших данных с именами категорий в модели Django
        categories_mapping = {
            "Бензин": [
                "АЗС",
                "Транспортировка",
                "Бизнес услуги",
                "Оптовые поставщики и производители",
                "Parking Lots and Garages",
            ],
            "Здоровье": [
                "Медицинский сервис",
                "Аптеки",
                "Hospitals",
                "Medical Services Health Practitioners - No Elsewhere Classified",
            ],
            "Машина": [
                "Автомобили - продажа / сервис",
                "Direct Marketing Insurance Services",
            ],
            "Продукты": [
                "Магазины продуктовые",
                "Grocery Stores and Supermarkets",
                "Miscellaneous Food Stores-Convenience Stores and Specialty Markets",
            ],
            "Рестораны": ["Ресторация / бары / кафе", "Eating Places and Restaurants"],
            "Собака": "Товары / услуги для животных",
            "Жилье": [
                "Аренда жилья / отели и мотели",
                "Lodging - Hotels, Motels, and Resorts",
            ],
            "Развлечения": [
                "Развлечения",
                "Amusement Parks, Circuses, Carnivals, and Fortune Tellers",
                "Theatrical Producers (except Motion Pictures) and Ticket Agencies",
            ],
            "Одежда": "Магазины одежды",
        }

        # Получаем имя категории в модели Django по имени категории из ваших данных
        mapped_category_name = (
            "Другое"  # Значение по умолчанию, если категория не найдена
        )

        for category, values in categories_mapping.items():
            if category_name in values:
                mapped_category_name = category
                break

        # Используем get_or_create для получения или создания категории в базе данных
        category, created = Category.objects.get_or_create(title=mapped_category_name)

        return category
