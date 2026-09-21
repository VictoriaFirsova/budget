import React, { useEffect, useState } from 'react';
import * as XLSX from 'xlsx';

import {
  createImportTemplate,
  fetchImportTemplates,
  importManualStatements,
  importStatements,
  previewImportStatements,
  updateImportTemplate,
} from '../../api';

const REQUIRED_FIELDS = ['date', 'amount', 'operation_name'];

const FIELD_LABELS = {
  date: 'Дата',
  amount: 'Сумма',
  operation_name: 'Описание операции',
  category: 'Категория',
  balance: 'Баланс',
  currency: 'Валюта',
  card: 'Карта/счет',
};

const PDF_HEADERS = ['date', 'amount', 'operation_name', 'category', 'balance', 'currency', 'card'];
const PDF_MAPPING = {
  date: 'date',
  amount: 'amount',
  operation_name: 'operation_name',
  category: 'category',
  balance: 'balance',
  currency: 'currency',
  card: 'card',
};

const HEADER_KEYWORDS = [
  'date',
  'дата',
  'description',
  'опис',
  'operation',
  'операц',
  'amount',
  'сумма',
  'currency',
  'валют',
  'paid',
  'выплач',
  'оплач',
  'получ',
  'balance',
  'баланс',
];

const guessColumns = (headers) => {
  const findHeader = (patterns) => (
    headers.find((header) => {
      const normalized = header.toLowerCase();
      return patterns.some((pattern) => normalized.includes(pattern));
    }) || ''
  );

  return {
    date: findHeader(['date', 'дата']),
    amount: findHeader(['amount', 'sum', 'сумма', 'paid out', 'debit', 'credit']),
    operation_name: findHeader(['description', 'operation', 'merchant', 'опис', 'операц', 'назнач']),
    category: findHeader(['category', 'категор', 'mcc']),
    balance: findHeader(['balance', 'баланс', 'остат']),
    currency: findHeader(['currency', 'валют']),
    card: findHeader(['card', 'account', 'счет', 'карта']),
  };
};

const toHeader = (value, index) => {
  const header = String(value || '').trim();
  return header || `Column ${index + 1}`;
};

const isFilledRow = (row) => row.some((cell) => String(cell || '').trim() !== '');

const getHeaderScore = (row) => row.reduce((score, cell) => {
  const normalized = String(cell || '').trim().toLowerCase();
  if (!normalized) {
    return score;
  }
  const keywordScore = HEADER_KEYWORDS.some((keyword) => normalized.includes(keyword)) ? 2 : 0;
  return score + keywordScore + 1;
}, 0);

const findHeaderIndex = (rows) => {
  let bestIndex = -1;
  let bestScore = 0;

  rows.slice(0, 40).forEach((row, index) => {
    if (!isFilledRow(row)) {
      return;
    }

    const score = getHeaderScore(row);
    if (score > bestScore) {
      bestIndex = index;
      bestScore = score;
    }
  });

  return bestIndex;
};

const looksLikeRepeatedHeaderRow = (row, headers) => {
  const headerValues = headers.map((header) => header.trim().toLowerCase()).filter(Boolean);
  const rowValues = row.map((cell) => String(cell || '').trim().toLowerCase()).filter(Boolean);

  if (rowValues.length === 0) {
    return false;
  }

  const matchingValues = rowValues.filter((value) => (
    headerValues.includes(value)
    || HEADER_KEYWORDS.some((keyword) => value.includes(keyword))
  ));
  return matchingValues.length >= Math.min(2, rowValues.length);
};

const getHeaderSignature = (headers) => (
  headers
    .map((header) => header.trim().toLowerCase())
    .filter(Boolean)
    .sort()
    .join('|')
);

const formatImportResult = (result) => {
  const invalidLabel = result.skipped_invalid === 0 ? 'ошибок нет' : `${result.skipped_invalid} с ошибками`;
  return `Импортировано: ${result.created}. Дубликатов: ${result.skipped_duplicates}. Пропущено: ${invalidLabel}.`;
};

const getImportErrorExamples = (result) => (result.errors || []).slice(0, 5);

const isPdfFile = (selectedFile) => selectedFile.name.toLowerCase().endsWith('.pdf');

const getApiErrorMessage = (error, fallbackMessage) => {
  const responseData = error.response?.data;
  if (!responseData) {
    return fallbackMessage;
  }
  if (typeof responseData === 'string') {
    return responseData;
  }
  if (responseData.detail) {
    return responseData.detail;
  }

  const firstFieldError = Object.values(responseData).find((value) => (
    Array.isArray(value) ? value.length > 0 : Boolean(value)
  ));
  if (Array.isArray(firstFieldError)) {
    return firstFieldError[0];
  }
  return firstFieldError || fallbackMessage;
};

const createEmptyPreviewRow = () => ({
  date: '',
  operation_name: '',
  amount: '',
  currency: '',
  category: '',
  my_category: '',
  card: '',
});

const FileUpload = ({ onImportComplete }) => {
  const [file, setFile] = useState(null);
  const [headers, setHeaders] = useState([]);
  const [previewRows, setPreviewRows] = useState([]);
  const [mapping, setMapping] = useState({});
  const [defaultCurrency, setDefaultCurrency] = useState('');
  const [defaultCard, setDefaultCard] = useState('');
  const [amountSign, setAmountSign] = useState('as_is');
  const [skipRows, setSkipRows] = useState(0);
  const [skipAfterHeader, setSkipAfterHeader] = useState(0);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [headerSignature, setHeaderSignature] = useState('');
  const [finalPreviewRows, setFinalPreviewRows] = useState([]);
  const [importResult, setImportResult] = useState(null);
  const [templateMessage, setTemplateMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        setTemplates(await fetchImportTemplates());
      } catch (err) {
        console.error('Не удалось загрузить шаблоны импорта:', err);
      }
    };

    loadTemplates();
  }, []);

  const onFileChange = async (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile || null);
    setHeaders([]);
    setPreviewRows([]);
    setMapping({});
    setDefaultCurrency('');
    setSkipRows(0);
    setSkipAfterHeader(0);
    setSelectedTemplateId('');
    setHeaderSignature('');
    setFinalPreviewRows([]);
    setImportResult(null);
    setTemplateMessage('');
    setError(null);

    if (!selectedFile) {
      return;
    }

    try {
      if (isPdfFile(selectedFile)) {
        const nextHeaderSignature = 'pdf-text-statement';
        const matchedTemplate = templates.find(
          (template) => template.header_signature === nextHeaderSignature,
        );

        setHeaders(PDF_HEADERS);
        setMapping(matchedTemplate?.columns || PDF_MAPPING);
        setDefaultCurrency(matchedTemplate?.default_currency || '');
        setDefaultCard(matchedTemplate?.default_card || '');
        setAmountSign(matchedTemplate?.amount_sign || 'as_is');
        setSkipRows(matchedTemplate?.skip_rows || 0);
        setSkipAfterHeader(matchedTemplate?.skip_after_header || 0);
        setHeaderSignature(nextHeaderSignature);
        setTemplateName(matchedTemplate?.name || selectedFile.name.replace(/\.[^.]+$/, ''));
        setSelectedTemplateId(matchedTemplate ? String(matchedTemplate.id) : '');
        return;
      }

      const workbook = XLSX.read(await selectedFile.arrayBuffer(), { type: 'array' });
      const worksheet = workbook.Sheets[workbook.SheetNames[0]];
      const rows = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });
      const headerIndex = findHeaderIndex(rows);

      if (headerIndex === -1) {
        setError('Файл пустой или не содержит таблицу.');
        return;
      }

      const nextHeaders = rows[headerIndex].map(toHeader);
      const detectedSkipAfterHeader = looksLikeRepeatedHeaderRow(rows[headerIndex + 1] || [], nextHeaders) ? 1 : 0;
      const nextPreviewRows = rows
        .slice(headerIndex + 1 + detectedSkipAfterHeader)
        .filter(isFilledRow)
        .slice(0, 50);
      const nextHeaderSignature = getHeaderSignature(nextHeaders);
      const matchedTemplate = templates.find(
        (template) => template.header_signature === nextHeaderSignature,
      );

      setHeaders(nextHeaders);
      setPreviewRows(nextPreviewRows);
      setSkipRows(headerIndex);
      setSkipAfterHeader(detectedSkipAfterHeader);
      setHeaderSignature(nextHeaderSignature);

      if (matchedTemplate) {
        setMapping(matchedTemplate.columns || {});
        setDefaultCurrency(matchedTemplate.default_currency || '');
        setDefaultCard(matchedTemplate.default_card || selectedFile.name.replace(/\.[^.]+$/, ''));
        setAmountSign(matchedTemplate.amount_sign || 'as_is');
        setSkipRows(matchedTemplate.skip_rows || headerIndex);
        setSkipAfterHeader(matchedTemplate.skip_after_header || detectedSkipAfterHeader);
        setSelectedTemplateId(String(matchedTemplate.id));
        setTemplateName(matchedTemplate.name);
      } else {
        setMapping(guessColumns(nextHeaders));
        setDefaultCard(selectedFile.name.replace(/\.[^.]+$/, ''));
        setTemplateName(selectedFile.name.replace(/\.[^.]+$/, ''));
      }
    } catch (err) {
      setError('Не удалось прочитать файл. Проверьте формат CSV, XLS, XLSX или PDF.');
    }
  };

  const buildImportSchema = () => ({
    columns: mapping,
    amount_sign: amountSign,
    dayfirst: true,
    default_currency: defaultCurrency.trim().toUpperCase(),
    default_card: defaultCard.trim().slice(0, 30),
    skip_rows: skipRows,
    skip_after_header: skipAfterHeader,
    infer_currency: true,
    infer_category_from_mcc: true,
  });

  const applyTemplate = (templateId) => {
    setSelectedTemplateId(templateId);
    setFinalPreviewRows([]);
    setTemplateMessage('');

    const template = templates.find((item) => String(item.id) === templateId);
    if (!template) {
      return;
    }

    setMapping(template.columns || {});
    setDefaultCurrency(template.default_currency || '');
    setDefaultCard(template.default_card || '');
    setAmountSign(template.amount_sign || 'as_is');
    setSkipRows(template.skip_rows || 0);
    setSkipAfterHeader(template.skip_after_header || 0);
    setTemplateName(template.name);
  };

  const validateRequiredMapping = () => {
    const missingFields = REQUIRED_FIELDS.filter((fieldName) => !mapping[fieldName]);
    if (missingFields.length > 0) {
      setError(`Заполните обязательные поля: ${missingFields.map((field) => FIELD_LABELS[field]).join(', ')}.`);
      return false;
    }
    return true;
  };

  const confirmMapping = async () => {
    if (!file) {
      setError('Сначала выберите файл.');
      return;
    }

    if (!validateRequiredMapping()) {
      return;
    }

    setIsPreviewLoading(true);
    setFinalPreviewRows([]);
    setTemplateMessage('');
    setError(null);

    try {
      const result = await previewImportStatements(file, buildImportSchema());
      setFinalPreviewRows(result.rows || []);
      if (result.errors?.length) {
        setError(`Часть строк не попала в итоговое превью: ${result.errors.join(' ')}`);
      }
    } catch (err) {
      const responseData = err.response?.data;
      const detail = responseData?.detail || 'Не удалось построить итоговое превью.';
      const errors = responseData?.errors || [];
      setError([detail, ...errors].join(' '));
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const backToMapping = () => {
    setFinalPreviewRows([]);
    setImportResult(null);
    setTemplateMessage('');
    setError(null);
  };

  const buildTemplatePayload = () => ({
    name: templateName.trim(),
    columns: mapping,
    amount_sign: amountSign,
    dayfirst: true,
    default_currency: defaultCurrency.trim().toUpperCase(),
    default_card: defaultCard.trim().slice(0, 30),
    skip_rows: skipRows,
    skip_after_header: skipAfterHeader,
    header_signature: headerSignature,
  });

  const persistTemplate = async ({ showMessage = true } = {}) => {
    if (!templateName.trim()) {
      setError('Введите название шаблона.');
      return null;
    }

    if (!headerSignature) {
      setError('Сначала загрузите файл, чтобы определить набор колонок.');
      return null;
    }

    const payload = buildTemplatePayload();
    const existingTemplate = templates.find((template) => (
      template.name.trim().toLowerCase() === payload.name.toLowerCase()
    ));
    const templateIdToUpdate = selectedTemplateId || existingTemplate?.id;

    const savedTemplate = templateIdToUpdate
      ? await updateImportTemplate(templateIdToUpdate, payload)
      : await createImportTemplate(payload);

    setTemplates((currentTemplates) => {
      const exists = currentTemplates.some((template) => template.id === savedTemplate.id);
      if (exists) {
        return currentTemplates.map((template) => (
          template.id === savedTemplate.id ? savedTemplate : template
        ));
      }
      return [...currentTemplates, savedTemplate];
    });
    setSelectedTemplateId(String(savedTemplate.id));
    if (showMessage) {
      setTemplateMessage(`Шаблон "${savedTemplate.name}" сохранён.`);
    }
    setError(null);
    return savedTemplate;
  };

  const saveTemplate = async () => {
    try {
      await persistTemplate();
    } catch (err) {
      setTemplateMessage('');
      setError(getApiErrorMessage(err, 'Не удалось сохранить шаблон.'));
    }
  };

  const onUpload = async () => {
    if (!file) {
      setError('Сначала выберите файл.');
      return;
    }

    if (!validateRequiredMapping()) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setImportResult(null);

    try {
      const savedTemplate = await persistTemplate({ showMessage: false });
      if (!savedTemplate) {
        setIsLoading(false);
        return;
      }
      setTemplateMessage(`Шаблон "${savedTemplate.name}" сохранён.`);
      const result = finalPreviewRows.length > 0
        ? await importManualStatements(finalPreviewRows)
        : await importStatements(file, buildImportSchema());
      setImportResult(result);
      setFinalPreviewRows([]);
      setHeaders([]);
      setPreviewRows([]);
      setFile(null);
      if (onImportComplete) {
        onImportComplete(result);
      }
    } catch (err) {
      const detail = getApiErrorMessage(err, 'Ошибка импорта файла.');
      const errors = err.response?.data?.errors || [];
      setError([detail, ...errors].join(' '));
    } finally {
      setIsLoading(false);
    }
  };

  const onMappingChange = (fieldName, columnName) => {
    setFinalPreviewRows([]);
    setTemplateMessage('');
    setMapping((currentMapping) => ({
      ...currentMapping,
      [fieldName]: columnName,
    }));
  };

  const updateSkipAfterHeader = (value) => {
    const nextSkipAfterHeader = Math.max(0, Number(value) || 0);
    setSkipAfterHeader(nextSkipAfterHeader);
    setFinalPreviewRows([]);
    setTemplateMessage('');
  };

  const updateFinalPreviewRow = (rowIndex, fieldName, value) => {
    setFinalPreviewRows((currentRows) => currentRows.map((row, index) => (
      index === rowIndex ? { ...row, [fieldName]: value } : row
    )));
    setImportResult(null);
  };

  const removeFinalPreviewRow = (rowIndex) => {
    setFinalPreviewRows((currentRows) => currentRows.filter((_, index) => index !== rowIndex));
    setImportResult(null);
  };

  const addFinalPreviewRow = () => {
    setFinalPreviewRows((currentRows) => [...currentRows, createEmptyPreviewRow()]);
    setImportResult(null);
  };

  const renderMappingSelect = (fieldName) => (
    <label key={fieldName}>
      {FIELD_LABELS[fieldName]}
      {REQUIRED_FIELDS.includes(fieldName) ? ' *' : ''}
      <select
        value={mapping[fieldName] || ''}
        onChange={(e) => onMappingChange(fieldName, e.target.value)}
      >
        <option value="">Не импортировать</option>
        {headers.map((header) => (
          <option key={header} value={header}>
            {header}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <section className="card import-card">
      <div className="card-header">
        <p className="eyebrow">Bank statement import</p>
        <h2>Импорт выписки</h2>
      </div>
      <p className="muted-text">
        Загрузите CSV, XLS, XLSX или текстовый PDF, проверьте превью и укажите, какие колонки
        соответствуют полям операции.
      </p>

      <div className="file-picker">
        <label className="file-picker-button" htmlFor="statement-file">
          Выбрать файл
        </label>
        <span className="file-picker-name">
          {file ? file.name : 'Файл не выбран'}
        </span>
        <input
          id="statement-file"
          type="file"
          accept=".csv,.xls,.xlsx,.pdf"
          onChange={onFileChange}
        />
      </div>

      {headers.length > 0 && (
        <>
          {finalPreviewRows.length === 0 ? (
            <>
              <h3>Шаблон импорта</h3>
              <div className="form-grid">
                <label>
                  Сохраненный шаблон
                  <select
                    value={selectedTemplateId}
                    onChange={(e) => applyTemplate(e.target.value)}
                  >
                    <option value="">Без шаблона</option>
                    {templates.map((template) => (
                      <option key={template.id} value={template.id}>
                        {template.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Название шаблона
                  <input
                    type="text"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    placeholder="Например, TBC CSV"
                  />
                </label>
              </div>

              <h3>Маппинг колонок</h3>
              <div className="mapping-grid">
                {Object.keys(FIELD_LABELS).map(renderMappingSelect)}
              </div>

              <div className="form-grid">
                <label>
                  Валюта для всех строк
                  <input
                    type="text"
                    maxLength="3"
                    value={defaultCurrency}
                    placeholder="Пусто = определить из строки"
                    onChange={(e) => {
                      setFinalPreviewRows([]);
                      setDefaultCurrency(e.target.value.toUpperCase());
                    }}
                  />
                </label>

                <label>
                  Карта/счет по умолчанию
                  <input
                    type="text"
                    value={defaultCard}
                    onChange={(e) => {
                      setFinalPreviewRows([]);
                      setDefaultCard(e.target.value);
                    }}
                  />
                </label>

                <label>
                  Знак суммы
                  <select
                    value={amountSign}
                    onChange={(e) => {
                      setFinalPreviewRows([]);
                      setAmountSign(e.target.value);
                    }}
                  >
                    <option value="as_is">Оставить как в файле</option>
                    <option value="invert">Инвертировать знак</option>
                    <option value="negative">Всегда расход</option>
                    <option value="positive">Всегда доход</option>
                  </select>
                </label>

                <label>
                  Пропустить строк после шапки
                  <input
                    type="number"
                    min="0"
                    value={skipAfterHeader}
                    onChange={(e) => updateSkipAfterHeader(e.target.value)}
                  />
                </label>
              </div>

              <div className="actions-row">
                <button type="button" onClick={confirmMapping} disabled={isPreviewLoading}>
                  {isPreviewLoading ? 'Проверяю...' : 'Подтвердить разметку'}
                </button>
                <button className="secondary-button" type="button" onClick={saveTemplate}>
                  Сохранить шаблон
                </button>
              </div>

              <h3>Исходное превью файла</h3>
              {previewRows.length > 0 ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        {headers.map((header) => (
                          <th key={header}>{header}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewRows.map((row, rowIndex) => (
                        <tr key={`${rowIndex}-${row.join('|')}`}>
                          {headers.map((header, cellIndex) => (
                            <td key={`${header}-${cellIndex}`}>
                              {String(row[cellIndex] ?? '')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="success-message">
                  Для PDF исходное превью строится на сервере. Нажмите «Подтвердить разметку»,
                  чтобы увидеть распознанные операции.
                </p>
              )}
            </>
          ) : (
            <>
              <div className="actions-row">
                <button className="secondary-button" type="button" onClick={backToMapping}>
                  Вернуться к разметке
                </button>
                <button type="button" onClick={onUpload} disabled={isLoading}>
                  {isLoading ? 'Импорт...' : 'Импортировать подтвержденные строки'}
                </button>
                <button className="secondary-button" type="button" onClick={saveTemplate}>
                  Сохранить шаблон
                </button>
                <button className="secondary-button" type="button" onClick={addFinalPreviewRow}>
                  Добавить строку
                </button>
              </div>

              <h3>Итоговая таблица для сохранения</h3>
              <p className="muted-text">
                Проверьте строки перед импортом. Можно исправить значения, удалить лишние операции
                или добавить пропущенную строку.
              </p>
              <div className="table-scroll">
                <table className="editable-preview-table">
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Операция</th>
                      <th>Сумма</th>
                      <th>Валюта</th>
                      <th>Категория банка</th>
                      <th>Категория приложения</th>
                      <th>Карта/счет</th>
                      <th>Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {finalPreviewRows.map((row, rowIndex) => (
                      <tr key={`${rowIndex}-${row.date}-${row.amount}`}>
                        <td>
                          <input
                            type="date"
                            value={row.date || ''}
                            onChange={(e) => updateFinalPreviewRow(rowIndex, 'date', e.target.value)}
                          />
                        </td>
                        <td>
                          <textarea
                            value={row.operation_name || ''}
                            onChange={(e) => updateFinalPreviewRow(rowIndex, 'operation_name', e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            value={row.amount || ''}
                            onChange={(e) => updateFinalPreviewRow(rowIndex, 'amount', e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            maxLength="3"
                            value={row.currency || ''}
                            onChange={(e) => updateFinalPreviewRow(rowIndex, 'currency', e.target.value.toUpperCase())}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            value={row.category || ''}
                            onChange={(e) => updateFinalPreviewRow(rowIndex, 'category', e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            value={row.my_category || ''}
                            onChange={(e) => updateFinalPreviewRow(rowIndex, 'my_category', e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            value={row.card || ''}
                            onChange={(e) => updateFinalPreviewRow(rowIndex, 'card', e.target.value)}
                          />
                        </td>
                        <td>
                          <button
                            className="danger-button table-action-button"
                            type="button"
                            onClick={() => removeFinalPreviewRow(rowIndex)}
                          >
                            Удалить
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      {importResult && (
        <div className="success-message">
          {templateMessage && <p>{templateMessage}</p>}
          <p>{formatImportResult(importResult)}</p>
          {getImportErrorExamples(importResult).length > 0 && (
            <>
              <p>Первые причины пропуска:</p>
              <ul className="import-error-list">
                {getImportErrorExamples(importResult).map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </>
          )}
    </div>
      )}

      {templateMessage && !importResult && (
        <p className="success-message">{templateMessage}</p>
      )}

      {error && <p className="alert" role="alert">{error}</p>}
    </section>
  );
};

export default FileUpload;
