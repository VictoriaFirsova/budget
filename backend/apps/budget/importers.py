import re
from functools import lru_cache
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import chardet
import pandas as pd
from pypdf import PdfReader

from .models import Category, Statement


REQUIRED_COLUMNS = ("date", "amount", "operation_name")
OPTIONAL_COLUMNS = ("category", "currency", "card", "balance")
PDF_COLUMNS = {
    "date": "date",
    "amount": "amount",
    "operation_name": "operation_name",
    "category": "category",
    "balance": "balance",
    "currency": "currency",
    "card": "card",
}
CURRENCY_ALIASES = {
    "GEL": ("GEL", "лари", "₾"),
    "USD": ("USD", "доллар США", "доллар", "$"),
    "EUR": ("EUR", "евро", "€"),
    "AMD": ("AMD", "армянский драм", "драм", "драмы", "֏"),
    "BYN": ("BYN", "белорусский рубль", "бел. руб", "руб."),
    "RUB": ("RUB", "RUR", "российский рубль", "рубль", "рубля", "рублей", "₽"),
}
CATEGORIES_MAPPING = {
    "Бензин": [
        "АЗС",
        "Транспортировка",
        "Бизнес услуги",
        "Оптовые поставщики и производители",
        "Service Stations (with or without Ancillary Services)",
    ],
    "Здоровье": [
        "Медицинский сервис",
        "Аптеки",
        "Hospitals",
        "Medical Services Health Practitioners - No Elsewhere Classified",
        "Drug Stores and Pharmacies",
    ],
    "Машина": [
        "Автомобили - продажа / сервис",
        "Direct Marketing Insurance Services",
        "Parking Lots and Garages",
        "Автомобиль",
    ],
    "Продукты": [
        "Магазины продуктовые",
        "Grocery Stores and Supermarkets",
        "Miscellaneous Food Stores-Convenience Stores and Specialty Markets",
    ],
    "Рестораны": ["Ресторация / бары / кафе", "Eating Places and Restaurants"],
    "Собака": ["Товары / услуги для животных"],
    "Жилье": [
        "Аренда жилья / отели и мотели",
        "Lodging - Hotels, Motels, and Resorts",
    ],
    "Развлечения": [
        "Развлечения",
        "Отдых и развлечения",
        "Amusement Parks, Circuses, Carnivals, and Fortune Tellers",
        "Theatrical Producers (except Motion Pictures) and Ticket Agencies",
    ],
    "Одежда": ["Магазины одежды", "Одежда и аксессуары"],
    "Красота": ["Beauty and Barber Shops"],
    "Наличные": ["Наличные"],
    "Связь": ["Telecommunication Services", "Коммунальные платежи, связь, интернет."],
    "Доставка": ["Courier Services-Air and Ground, and Freight Forwarders"],
    "Электроника": ["Electronics Stores"],
}
FALLBACK_MCC_DESCRIPTIONS = {
    5411: "Grocery Stores and Supermarkets",
    5499: "Miscellaneous Food Stores-Convenience Stores and Specialty Markets",
    5541: "Service Stations (with or without Ancillary Services)",
    5812: "Eating Places and Restaurants",
    5912: "Drug Stores and Pharmacies",
    5999: "Miscellaneous and Specialty Retail Stores",
    7011: "Lodging - Hotels, Motels, and Resorts",
}


@dataclass
class ImportResult:
    created: int = 0
    skipped_duplicates: int = 0
    skipped_invalid: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ImportPreviewResult:
    rows: list[dict[str, str]] = field(default_factory=list)
    skipped_invalid: int = 0
    errors: list[str] = field(default_factory=list)


class StatementImportError(Exception):
    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


def import_statements_from_file(
    uploaded_file: Any, schema: dict[str, Any], user: Any
) -> ImportResult:
    mapping = schema.get("columns", schema)
    _validate_mapping(mapping)
    _validate_user(user)

    df = _read_uploaded_file(uploaded_file, schema)
    _validate_source_columns(df, mapping)
    df = _drop_non_data_rows(df, mapping)

    result = ImportResult()

    for source_index, row in df.iterrows():
        try:
            statement_data = _build_statement_data(row, mapping, schema)
        except ValueError as exc:
            result.skipped_invalid += 1
            if len(result.errors) < 20:
                result.errors.append(f"Row {cast(int, source_index) + 2}: {exc}")
            continue

        if _save_statement_data(statement_data, user):
            result.skipped_duplicates += 1
            continue

        result.created += 1

    return result


def import_statements_from_rows(rows: list[dict[str, Any]], user: Any) -> ImportResult:
    _validate_user(user)

    result = ImportResult()
    for row_index, row in enumerate(rows, start=1):
        try:
            statement_data, my_category_title = _build_manual_statement_data(row)
        except ValueError as exc:
            result.skipped_invalid += 1
            if len(result.errors) < 20:
                result.errors.append(f"Row {row_index}: {exc}")
            continue

        if _save_statement_data(statement_data, user, my_category_title):
            result.skipped_duplicates += 1
            continue

        result.created += 1

    return result


def preview_statements_from_file(
    uploaded_file: Any,
    schema: dict[str, Any],
    user: Any | None = None,
    limit: int | None = None,
) -> ImportPreviewResult:
    mapping = schema.get("columns", schema)
    _validate_mapping(mapping)

    df = _read_uploaded_file(uploaded_file, schema)
    _validate_source_columns(df, mapping)
    df = _drop_non_data_rows(df, mapping)

    result = ImportPreviewResult()
    for source_index, row in df.iterrows():
        if limit is not None and len(result.rows) >= limit:
            break

        try:
            statement_data = _build_statement_data(row, mapping, schema)
        except ValueError as exc:
            result.skipped_invalid += 1
            if len(result.errors) < 20:
                result.errors.append(f"Row {cast(int, source_index) + 2}: {exc}")
            continue

        result.rows.append(_serialize_preview_row(statement_data))

    return result


def _read_uploaded_file(uploaded_file: Any, schema: dict[str, Any]) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    skip_rows = int(schema.get("skip_rows") or 0)
    skip_after_header = int(schema.get("skip_after_header") or 0)
    uploaded_file.seek(0)

    if file_name.endswith(".csv"):
        raw_content = uploaded_file.read()
        encoding = chardet.detect(raw_content).get("encoding") or "utf-8"
        df = pd.read_csv(
            BytesIO(raw_content),
            sep=None,
            engine="python",
            encoding=encoding,
            skiprows=skip_rows,
            dtype=str,
        )
        return _drop_rows_after_header(df, skip_after_header)

    if file_name.endswith(".xlsx"):
        df = pd.read_excel(
            uploaded_file,
            skiprows=skip_rows,
            dtype=str,
            engine="openpyxl",
        )
        return _drop_rows_after_header(df, skip_after_header)

    if file_name.endswith(".xls"):
        df = pd.read_excel(
            uploaded_file,
            skiprows=skip_rows,
            dtype=str,
            engine="xlrd",
        )
        return _drop_rows_after_header(df, skip_after_header)

    if file_name.endswith(".pdf"):
        return _read_pdf_statement(uploaded_file)

    raise StatementImportError(
        "Unsupported file format. Upload CSV, XLS, XLSX, or PDF."
    )


def _read_pdf_statement(uploaded_file: Any) -> pd.DataFrame:
    uploaded_file.seek(0)
    try:
        reader = PdfReader(uploaded_file)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise StatementImportError("Could not read PDF text.") from exc

    records = _parse_pdf_statement_text(text)
    if not records:
        raise StatementImportError(
            "Не удалось найти операции в PDF.",
            [
                "Поддерживаются текстовые PDF-выписки, где операции можно распознать по дате, времени, сумме и остатку.",
            ],
        )

    return pd.DataFrame(records, columns=list(PDF_COLUMNS.values()))


def _parse_pdf_statement_text(text: str) -> list[dict[str, str]]:
    currency = _extract_pdf_account_currency(text)
    card = _extract_pdf_card(text)
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    detail_parts: list[str] = []

    for raw_line in text.splitlines():
        line = _clean_text(raw_line)
        if not line or _is_pdf_noise_line(line):
            continue

        match = re.match(
            r"^(?P<date>\d{2}\.\d{2}\.\d{4})\s+"
            r"(?P<time>\d{2}:\d{2})\s+"
            r"(?P<category>.+?)\s+"
            r"(?P<amount>[+-]?\d[\d\s]*,\d{2})\s+"
            r"(?P<balance>[+-]?\d[\d\s]*,\d{2})$",
            line,
        )
        if match:
            _append_pdf_record(records, current, detail_parts)
            current = _build_pdf_record(match.groupdict(), currency, card)
            detail_parts = []
            continue

        if current:
            detail = _clean_pdf_operation_detail(line)
            if detail:
                detail_parts.append(detail)

    _append_pdf_record(records, current, detail_parts)
    return (
        records
        or _parse_pdf_statement_compact_text(text, currency, card)
        or _parse_alfa_pdf_statement_text(text)
    )


def _parse_alfa_pdf_statement_text(text: str) -> list[dict[str, str]]:
    currency = _extract_pdf_account_currency(text) or "RUB"
    card = _extract_alfa_account(text)
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    detail_parts: list[str] = []
    in_operations = False

    for raw_line in text.splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        if line.casefold().startswith("операции по счету"):
            in_operations = True
            continue
        if not in_operations or _is_alfa_pdf_noise_line(line):
            continue

        start_match = re.match(
            r"^(?P<date>\d{2}\.\d{2}\.\d{4})\s+"
            r"(?P<code>\S+)\s+"
            r"(?P<description>.+)$",
            line,
        )
        if start_match:
            _append_alfa_pdf_record(records, current, detail_parts)
            current = _build_alfa_pdf_record(start_match.groupdict(), currency, card)
            detail_parts = []
            inline_amount = _pop_alfa_amount(current)
            if inline_amount:
                current["amount"] = inline_amount
                _append_alfa_pdf_record(records, current, detail_parts)
                current = None
            continue

        amount_match = re.match(
            r"^(?P<amount>[+\-\u2212]?\d[\d\s]*,\d{2})\s+(?P<currency>[A-Z]{3})$", line
        )
        if amount_match and current:
            current["amount"] = amount_match.group("amount").replace("\u2212", "-")
            current["currency"] = (
                _extract_currency(amount_match.group("currency")) or current["currency"]
            )
            _append_alfa_pdf_record(records, current, detail_parts)
            current = None
            detail_parts = []
            continue

        if current:
            detail_parts.append(line)

    _append_alfa_pdf_record(records, current, detail_parts)
    return records


def _build_alfa_pdf_record(
    match_data: dict[str, str], currency: str, card: str
) -> dict[str, str]:
    description = _clean_text(match_data["description"])
    category = _resolve_alfa_category(description)
    return {
        "date": match_data["date"],
        "amount": "",
        "operation_name": description,
        "category": category,
        "balance": "",
        "currency": currency,
        "card": card,
    }


def _append_alfa_pdf_record(
    records: list[dict[str, str]],
    current: dict[str, str] | None,
    detail_parts: list[str],
) -> None:
    if current is None or not current.get("amount"):
        return

    details = " ".join(detail_parts)
    if details:
        current["operation_name"] = f"{current['operation_name']} {details}"
        current["category"] = _resolve_alfa_category(current["operation_name"])
    records.append(current)


def _pop_alfa_amount(record: dict[str, str]) -> str:
    match = re.search(
        r"(?P<amount>[+\-\u2212]?\d[\d\s]*,\d{2})\s+(?:RUR|RUB)\s*$",
        record["operation_name"],
    )
    if not match:
        return ""

    record["operation_name"] = _clean_text(record["operation_name"][: match.start()])
    record["category"] = _resolve_alfa_category(record["operation_name"])
    return match.group("amount").replace("\u2212", "-")


def _resolve_alfa_category(description: str) -> str:
    normalized = description.casefold()
    mcc_description = _lookup_mcc_description(description)
    if mcc_description:
        return mcc_description
    if "жку" in normalized or "мосэнергосбыт" in normalized or "mcc4900" in normalized:
        return "Коммунальные платежи, связь, интернет."
    if "ozon" in normalized or "wildberries" in normalized:
        return "Покупки"
    if "комиссия" in normalized:
        return "Комиссия"
    if "перевод" in normalized:
        return "Перевод"
    if "операция по карте" in normalized:
        return "Операция по карте"
    return "Другое"


def _parse_pdf_statement_compact_text(
    text: str, currency: str, card: str
) -> list[dict[str, str]]:
    compact_text = re.sub(r"\s+", " ", text)
    pattern = re.compile(
        r"(?P<date>\d{2}\.\d{2}\.\d{4})\s+"
        r"(?P<time>\d{2}:\d{2})\s+"
        r"(?P<category>.+?)\s+"
        r"(?P<amount>[+\-\u2212]?\d[\d\s]*,\d{2})\s+"
        r"(?P<balance>[+\-\u2212]?\d[\d\s]*,\d{2})"
        r"(?=\s+\d{2}\.\d{2}\.\d{4}\s+(?:\d{2}:\d{2}|\d{6})|\s+Продолжение|\s+--|\s*$)",
        re.IGNORECASE,
    )

    records = []
    for match in pattern.finditer(compact_text):
        record = _build_pdf_record(match.groupdict(), currency, card)
        record["operation_name"] = _strip_pdf_header_text(record["operation_name"])
        record["category"] = _strip_pdf_header_text(record["category"])
        if record["category"]:
            records.append(record)
    return records


def _build_pdf_record(
    match_data: dict[str, str], currency: str, card: str
) -> dict[str, str]:
    raw_amount = _clean_text(match_data["amount"]).replace("\u2212", "-")
    amount = raw_amount if raw_amount.startswith(("+", "-")) else f"-{raw_amount}"
    category = _clean_text(match_data["category"])
    return {
        "date": match_data["date"],
        "amount": amount,
        "operation_name": category,
        "category": category,
        "balance": _clean_text(match_data["balance"]).replace("\u2212", "-"),
        "currency": currency,
        "card": card,
    }


def _strip_pdf_header_text(value: str) -> str:
    markers = (
        "Расшифровка операций",
        "ОСТАТОК СРЕДСТВ",
        "В валюте счёта",
        "В валюте счета",
    )
    cleaned_value = _clean_text(value)
    for marker in markers:
        if marker in cleaned_value:
            cleaned_value = cleaned_value.split(marker, 1)[-1]
    return _clean_text(cleaned_value)


def _append_pdf_record(
    records: list[dict[str, str]],
    current: dict[str, str] | None,
    detail_parts: list[str],
) -> None:
    if current is None:
        return

    operation_detail = " ".join(detail_parts)
    if operation_detail:
        separator = " " if current["operation_name"].endswith((".", "!", "?")) else ". "
        current[
            "operation_name"
        ] = f"{current['operation_name']}{separator}{operation_detail}"
    records.append(current)


def _clean_pdf_operation_detail(line: str) -> str:
    return _clean_text(re.sub(r"^\d{2}\.\d{2}\.\d{4}\s+\d{6}\s+", "", line))


def _extract_pdf_account_currency(text: str) -> str:
    match = re.search(r"Валюта\s+([^\n]+)", text, re.IGNORECASE)
    if not match:
        return ""
    return _extract_currency(match.group(1))


def _extract_pdf_card(text: str) -> str:
    match = re.search(r"Карта\s+([^\n]+)", text, re.IGNORECASE)
    if not match:
        return ""
    return _clean_text(match.group(1))[:30]


def _extract_alfa_account(text: str) -> str:
    match = re.search(r"Номер счета\s+([^\n]+)", text, re.IGNORECASE)
    if not match:
        return ""
    account_number = re.sub(r"\s+", "", match.group(1))
    return f"Счет {account_number}"[:30]


def _is_alfa_pdf_noise_line(line: str) -> bool:
    normalized = line.casefold()
    noise_prefixes = (
        "т.т. трофимова",
        "уполномоченное лицо",
        "(подпись сотрудника",
        "страница",
        "выписка по счету",
        "номер счета",
        "дата открытия счета",
        "валюта счета",
        "тип счета",
        "дата формирования",
        "выписки",
        "клиент",
        "адрес регистрации",
        "за период",
        "входящий остаток",
        "поступления",
        "расходы",
        "исходящий остаток",
        "платежный лимит",
        "на дату формирования",
        "текущий баланс",
        "общая задолженность",
        "дата проводки",
        "в валюте счета",
        "операции по счету",
    )
    return (
        normalized.startswith(noise_prefixes)
        or re.match(r"^--\s*\d+\s+of\s+\d+\s*--$", normalized) is not None
    )


def _is_pdf_noise_line(line: str) -> bool:
    normalized = line.casefold()
    noise_prefixes = (
        "дата операции",
        "дата обработки",
        "и код авторизации",
        "категория",
        "описание операции",
        "сумма в валюте",
        "остаток средств",
        "в валюте",
        "продолжение на следующей странице",
        "выписка по счёту",
        "действителен",
        "для проверки",
        "зайдите",
        "нажмите",
        "получите",
        "предоставляя",
        "заказано",
        "владелец",
        "номер счёта",
        "дата открытия",
        "дата закрытия",
        "итого по операциям",
        "расшифровка операций",
        "страница",
    )
    return (
        normalized.startswith(noise_prefixes)
        or re.match(r"^--\s*\d+\s+of\s+\d+\s*--$", normalized) is not None
    )


def _drop_rows_after_header(df: pd.DataFrame, skip_after_header: int) -> pd.DataFrame:
    if skip_after_header <= 0:
        return df
    return df.iloc[skip_after_header:].reset_index(drop=True)


def _validate_mapping(mapping: dict[str, Any]) -> None:
    missing = [
        field_name for field_name in REQUIRED_COLUMNS if not mapping.get(field_name)
    ]
    if missing:
        raise StatementImportError(
            "Missing required column mapping.",
            [f"Map column for '{field_name}'." for field_name in missing],
        )


def _validate_user(user: Any) -> None:
    if not getattr(user, "is_authenticated", False):
        raise StatementImportError("Authenticated user is required.")


def _validate_source_columns(df: pd.DataFrame, mapping: dict[str, Any]) -> None:
    source_columns = {str(column) for column in df.columns}
    configured_columns = _configured_source_columns(mapping)
    missing = [
        column_name
        for column_name in configured_columns
        if column_name not in source_columns
    ]
    if missing:
        raise StatementImportError(
            "Mapped columns were not found in the uploaded file.",
            [f"Column '{column_name}' was not found." for column_name in missing],
        )


def _configured_source_columns(mapping: dict[str, Any]) -> list[str]:
    return [
        column_name
        for field_name, column_name in mapping.items()
        if field_name in (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS) and column_name
    ]


def _drop_non_data_rows(df: pd.DataFrame, mapping: dict[str, Any]) -> pd.DataFrame:
    configured_columns = _configured_source_columns(mapping)
    if not configured_columns:
        return df

    row_mask = df.apply(
        lambda row: _has_mapped_values(row, configured_columns)
        and not _looks_like_header_row(row, configured_columns),
        axis=1,
    )
    return df.loc[row_mask]


def _has_mapped_values(row: pd.Series, columns: list[str]) -> bool:
    return any(not _is_empty(row.get(column_name)) for column_name in columns)


def _looks_like_header_row(row: pd.Series, columns: list[str]) -> bool:
    values = [
        _clean_text(row.get(column_name)).casefold()
        for column_name in columns
        if not _is_empty(row.get(column_name))
    ]
    if not values:
        return False

    headers = {column_name.casefold() for column_name in columns}
    matches = sum(1 for value in values if value in headers)
    return matches >= min(2, len(values))


def _build_statement_data(
    row: pd.Series,
    mapping: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    statement_date = _parse_date(
        _get_mapped_value(row, mapping, "date"),
        schema.get("date_format") or None,
        bool(schema.get("dayfirst", True)),
    )
    amount = _parse_amount(_get_mapped_value(row, mapping, "amount"))
    amount_sign = schema.get("amount_sign", "as_is")
    if amount_sign == "invert":
        amount *= Decimal("-1")
    elif amount_sign == "negative":
        amount = -abs(amount)
    elif amount_sign == "positive":
        amount = abs(amount)

    operation_name = _clean_text(_get_mapped_value(row, mapping, "operation_name"))
    if not operation_name:
        raise ValueError("operation description is empty")

    category = _resolve_source_category(
        _get_mapped_value(row, mapping, "category"),
        operation_name,
    )
    currency = _resolve_currency(
        schema.get("default_currency"),
        _get_mapped_value(row, mapping, "currency"),
        operation_name,
        _get_mapped_value(row, mapping, "amount"),
        category,
    )
    card = (
        _clean_text(_get_mapped_value(row, mapping, "card"))
        or _clean_text(schema.get("default_card"))
        or "Unknown"
    )[:30]

    return {
        "date": statement_date,
        "operation_name": operation_name[:200],
        "amount": amount,
        "currency": currency,
        "category": category[:400],
        "card": card,
    }


def _get_mapped_value(row: pd.Series, mapping: dict[str, Any], field_name: str) -> Any:
    column_name = mapping.get(field_name)
    if not column_name:
        return None
    return row.get(column_name)


def _build_manual_statement_data(row: dict[str, Any]) -> tuple[dict[str, Any], str]:
    statement_date = _parse_date(row.get("date"), None, True)
    amount = _parse_amount(row.get("amount"))
    operation_name = _clean_text(row.get("operation_name"))
    if not operation_name:
        raise ValueError("operation description is empty")

    category = _clean_text(row.get("category")) or "Другое"
    currency = _resolve_currency(row.get("currency"))
    card = (_clean_text(row.get("card")) or "Unknown")[:30]
    my_category_title = _clean_text(row.get("my_category"))

    return (
        {
            "date": statement_date,
            "operation_name": operation_name[:200],
            "amount": amount,
            "currency": currency,
            "category": category[:400],
            "card": card,
        },
        my_category_title,
    )


def _parse_date(value: Any, date_format: str | None, dayfirst: bool) -> date:
    if _is_empty(value):
        raise ValueError("date is empty")

    parsed = pd.to_datetime(
        value,
        format=date_format,
        dayfirst=dayfirst,
        errors="coerce",
    )
    if pd.isna(parsed):
        raise ValueError(f"cannot parse date '{value}'")
    return parsed.date()


def _parse_amount(value: Any) -> Decimal:
    if _is_empty(value):
        raise ValueError("amount is empty")

    text = str(value).strip().replace("\xa0", " ")
    is_negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^\d,.\-]", "", text)

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    if is_negative and not text.startswith("-"):
        text = f"-{text}"

    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"cannot parse amount '{value}'") from exc


def _resolve_currency(*values: Any) -> str:
    for value in values:
        currency = _extract_currency(value)
        if currency:
            return currency
    raise ValueError("currency is empty")


def _extract_currency(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""

    normalized_text = text.casefold()
    for currency, aliases in CURRENCY_ALIASES.items():
        for alias in aliases:
            alias_text = alias.casefold()
            if len(alias_text) == 3 and alias_text.isalpha():
                if re.search(
                    rf"(?<![A-ZА-Я]){re.escape(alias_text)}(?![A-ZА-Я])",
                    normalized_text,
                    re.IGNORECASE,
                ):
                    return currency
            elif alias_text in normalized_text:
                return currency
    return ""


def _resolve_source_category(category_value: Any, operation_name: str) -> str:
    category = _clean_text(category_value)
    if category and category.casefold() not in {"nan", "none", "другое"}:
        return _lookup_mcc_description(category) or category

    return _lookup_mcc_description(operation_name) or "Другое"


def _lookup_mcc_description(text: Any) -> str:
    description = _clean_text(text)
    if not description:
        return ""

    if "ATM CASH" in description.upper():
        return "Наличные"

    match = re.search(r"\bMCC\D*(\d{4})\b", description, re.IGNORECASE)
    if not match:
        return ""

    mcc_description = _load_mcc_descriptions().get(int(match.group(1)), "")
    return _clean_text(mcc_description)


@lru_cache(maxsize=1)
def _load_mcc_descriptions() -> dict[int, str]:
    mcc_path = Path(__file__).with_name("mcc.xls")
    if not mcc_path.exists():
        return FALLBACK_MCC_DESCRIPTIONS

    try:
        mcc_data = pd.read_excel(
            mcc_path,
            header=None,
            index_col=0,
            names=["descr"],
            engine="xlrd",
        )
    except Exception:
        return {}

    descriptions: dict[int, str] = {}
    for index, row in mcc_data.iterrows():
        if pd.isna(cast(Any, index)):
            continue
        descriptions[int(cast(Any, index))] = _clean_text(row["descr"])
    return {**FALLBACK_MCC_DESCRIPTIONS, **descriptions}


def _get_category(category_name: str, user: Any) -> Category:
    mapped_category_name = _map_category_name(category_name)
    return _get_or_create_user_category(mapped_category_name, user)


def _get_or_create_user_category(category_name: str, user: Any) -> Category:
    normalized_category = _clean_text(category_name) or "Другое"
    category, _ = Category.objects.get_or_create(user=user, title=normalized_category)
    return category


def _save_statement_data(
    statement_data: dict[str, Any],
    user: Any,
    my_category_title: str = "",
) -> bool:
    if Statement.objects.filter(user=user, **statement_data).exists():
        return True

    my_category = (
        _get_or_create_user_category(my_category_title, user)
        if my_category_title
        else _get_category(statement_data["category"], user)
    )
    Statement.objects.create(**statement_data, my_category=my_category, user=user)
    return False


def _map_category_name(category_name: str) -> str:
    normalized_category = _clean_text(category_name)

    for category, values in CATEGORIES_MAPPING.items():
        if normalized_category in values:
            return category

    return "Другое"


def _serialize_preview_row(statement_data: dict[str, Any]) -> dict[str, str]:
    return {
        "date": statement_data["date"].isoformat(),
        "operation_name": statement_data["operation_name"],
        "amount": str(statement_data["amount"]),
        "currency": statement_data["currency"],
        "category": statement_data["category"],
        "my_category": _map_category_name(statement_data["category"]),
        "card": statement_data["card"],
    }


def _clean_text(value: Any) -> str:
    if _is_empty(value):
        return ""
    return str(value).strip()


def _is_empty(value: Any) -> bool:
    return value is None or pd.isna(value) or str(value).strip() == ""
