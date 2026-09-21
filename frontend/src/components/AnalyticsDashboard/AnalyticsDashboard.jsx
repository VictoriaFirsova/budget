import React, { useEffect, useMemo, useState } from 'react';
import { fetchAnalytics } from '../../api';

const PERIOD_OPTIONS = [
  { value: 'week', label: 'Неделя' },
  { value: 'month', label: 'Месяц' },
  { value: 'year', label: 'Год' },
  { value: 'custom', label: 'Вручную' },
];

const PIE_COLORS = [
  '#ffb15f',
  '#f39a43',
  '#d75f5f',
  '#c7792e',
  '#f5d36a',
  '#8fcf9a',
  '#7fb7b2',
  '#64666a',
];

const toMoney = (value, currency) => `${Number(value || 0).toLocaleString('ru-RU', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})} ${currency}`;

const compactFilters = (filters) => Object.fromEntries(
  Object.entries(filters).filter(([, value]) => value !== ''),
);

const groupByCurrency = (rows) => rows.reduce((groups, row) => {
  const nextGroups = { ...groups };
  nextGroups[row.currency] = [...(nextGroups[row.currency] || []), row];
  return nextGroups;
}, {});

const toPoint = (center, radius, angle) => {
  const radians = ((angle - 90) * Math.PI) / 180;
  return {
    x: center + radius * Math.cos(radians),
    y: center + radius * Math.sin(radians),
  };
};

const describeSlice = (center, radius, startAngle, endAngle) => {
  if (endAngle - startAngle >= 359.99) {
    return [
      `M ${center} ${center - radius}`,
      `A ${radius} ${radius} 0 1 0 ${center} ${center + radius}`,
      `A ${radius} ${radius} 0 1 0 ${center} ${center - radius}`,
      'Z',
    ].join(' ');
  }

  const start = toPoint(center, radius, endAngle);
  const end = toPoint(center, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? 0 : 1;
  return [
    `M ${center} ${center}`,
    `L ${start.x} ${start.y}`,
    `A ${radius} ${radius} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`,
    'Z',
  ].join(' ');
};

const buildPieRows = (rows) => {
  return [...rows]
    .filter((row) => Number(row.amount) > 0)
    .sort((a, b) => Number(b.amount) - Number(a.amount));
};

const buildPieSlices = (rows) => {
  const pieRows = buildPieRows(rows);
  const total = pieRows.reduce((sum, row) => sum + Number(row.amount), 0);
  let currentAngle = 0;

  return pieRows.map((row, index) => {
    const value = Number(row.amount);
    const angle = total > 0 ? (value / total) * 360 : 0;
    const startAngle = currentAngle;
    const endAngle = currentAngle + angle;
    const midAngle = startAngle + angle / 2;
    currentAngle = endAngle;

    return {
      ...row,
      index: index + 1,
      value,
      color: PIE_COLORS[index % PIE_COLORS.length],
      path: describeSlice(160, 96, startAngle, endAngle),
      numberPoint: toPoint(160, 72, midAngle),
      percent: total > 0 ? Math.round((value / total) * 100) : 0,
    };
  });
};

const CategoryPieChart = ({ currency, rows }) => {
  const slices = buildPieSlices(rows);

  return (
    <div className="pie-chart-card">
      <div className="pie-chart-header">
        <span>{currency}</span>
        <strong>{toMoney(rows.reduce((sum, row) => sum + Number(row.amount), 0), currency)}</strong>
      </div>
      <svg className="category-pie" viewBox="0 0 320 320" role="img" aria-label={`Расходы по категориям ${currency}`}>
        {slices.map((slice) => (
          <g key={`${currency}-${slice.category}`}>
            <path d={slice.path} fill={slice.color} />
          </g>
        ))}
        {slices.map((slice) => (
          <g key={`${currency}-${slice.category}-number`}>
            <circle cx={slice.numberPoint.x} cy={slice.numberPoint.y} r="13" fill="#fff" />
            <circle cx={slice.numberPoint.x} cy={slice.numberPoint.y} r="11" fill={slice.color} />
            <text
              x={slice.numberPoint.x}
              y={slice.numberPoint.y + 4}
              textAnchor="middle"
              className="pie-number"
            >
              {slice.index}
            </text>
          </g>
        ))}
        <circle cx="160" cy="160" r="48" fill="#fff" />
        <text x="160" y="154" textAnchor="middle" className="pie-center-title">Расходы</text>
        <text x="160" y="174" textAnchor="middle" className="pie-center-value">{currency}</text>
      </svg>
      <div className="pie-legend">
        {slices.map((slice) => (
          <span key={`${currency}-${slice.category}-legend`}>
            <i style={{ background: slice.color }} />
            <strong>{slice.index}. {slice.category}</strong>
            <small>{slice.percent}% · {toMoney(slice.amount, currency)}</small>
          </span>
        ))}
      </div>
    </div>
  );
};

const AnalyticsDashboard = () => {
  const [period, setPeriod] = useState('month');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [analytics, setAnalytics] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadAnalytics = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const filters = compactFilters({
          period,
          date_from: period === 'custom' ? dateFrom : '',
          date_to: period === 'custom' ? dateTo : '',
        });
        setAnalytics(await fetchAnalytics(filters));
      } catch (loadError) {
        setError(loadError.response?.data?.detail || 'Не удалось загрузить дашборды.');
      } finally {
        setIsLoading(false);
      }
    };

    if (period !== 'custom' || (dateFrom && dateTo)) {
      loadAnalytics();
    }
  }, [period, dateFrom, dateTo]);

  const categoryGroups = useMemo(
    () => groupByCurrency(analytics?.category_expenses || []),
    [analytics],
  );
  const timelineGroups = useMemo(
    () => groupByCurrency(analytics?.timeline || []),
    [analytics],
  );

  const hasData = analytics && analytics.counts.total > 0;

  return (
    <section className="analytics-page">
      <div className="card analytics-hero">
        <div className="analytics-hero-main">
          <div className="card-header">
            <p className="eyebrow">Budget analytics</p>
            <h2>Дашборды</h2>
          </div>
          <p className="muted-text">
            Суммы в разных валютах не смешиваются: каждая метрика считается отдельно для GEL,
            USD, AMD и других валют.
          </p>
        </div>

        <div className="analytics-hero-side">
          <div className="period-toolbar">
            <div className="period-buttons" aria-label="Выбор периода">
              {PERIOD_OPTIONS.map((option) => (
                <button
                  className={period === option.value ? 'period-button active' : 'period-button'}
                  key={option.value}
                  type="button"
                  onClick={() => setPeriod(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>

            {period === 'custom' && (
              <div className="custom-period">
                <label>
                  Дата от
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                  />
                </label>
                <label>
                  Дата до
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                  />
                </label>
              </div>
            )}
          </div>

          {analytics && (
            <div className="analytics-range">
              <span>Период: {analytics.date_from} - {analytics.date_to}</span>
              <strong>{analytics.counts.total} операций</strong>
            </div>
          )}
        </div>
      </div>

      {isLoading && <p className="success-message">Загружаю аналитику...</p>}
      {error && <p className="alert" role="alert">{error}</p>}

      {analytics && (
        <>
          {!hasData && (
            <p className="success-message">
              За выбранный период операций нет. Импортируйте выписку или выберите другой период.
            </p>
          )}

          {hasData && (
            <>
              <div className="metric-grid">
                {analytics.summary.map((row) => (
                  <article className="card metric-card" key={row.currency}>
                    <p className="eyebrow">{row.currency}</p>
                    <h3>{toMoney(row.balance, row.currency)}</h3>
                    <div className="metric-lines">
                      <span>Доходы: {toMoney(row.income, row.currency)}</span>
                      <span>Расходы: {toMoney(row.expense, row.currency)}</span>
                    </div>
                  </article>
                ))}
                <article className="card metric-card">
                  <p className="eyebrow">Операции</p>
                  <h3>{analytics.counts.total}</h3>
                  <div className="metric-lines">
                    <span>Доходов: {analytics.counts.income}</span>
                    <span>Расходов: {analytics.counts.expense}</span>
                  </div>
                </article>
              </div>

              <div className="dashboard-grid analytics-grid">
                <section className="card analytics-card analytics-card-wide">
                  <div className="card-header">
                    <p className="eyebrow">Расходы</p>
                    <h2>По категориям</h2>
                  </div>
                  {Object.entries(categoryGroups).map(([currency, rows]) => {
                    const maxAmount = Math.max(...rows.map((row) => Number(row.amount)));
                    return (
                      <div className="analytics-list-block" key={currency}>
                        <h3>{currency}</h3>
                        <div className="analytics-bars">
                          {rows.map((row) => (
                            <div className="analytics-bar-row" key={`${row.category}-${row.currency}`}>
                              <div className="analytics-bar-meta">
                                <span>{row.category}</span>
                                <strong>{toMoney(row.amount, row.currency)}</strong>
                              </div>
                              <div className="analytics-bar-track">
                                <div
                                  className="analytics-bar-fill"
                                  style={{ width: `${Math.max(6, (Number(row.amount) / maxAmount) * 100)}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </section>

                <section className="card analytics-card">
                  <div className="card-header">
                    <p className="eyebrow">Список</p>
                    <h2>Все категории</h2>
                  </div>
                  {Object.entries(categoryGroups).map(([currency, rows]) => (
                    <div className="analytics-list-block" key={currency}>
                      <h3>{currency}</h3>
                      <ul className="analytics-top-list">
                        {rows.filter((row) => Number(row.amount) > 0).map((row) => (
                          <li key={`${row.category}-${row.currency}`}>
                            <span>{row.category}</span>
                            <strong>{toMoney(row.amount, row.currency)}</strong>
                          </li>
                        ))}
                      </ul>
                    </div>
                    ))}
                </section>
              </div>

              <section className="card analytics-card analytics-pie-section">
                <div className="card-header">
                  <p className="eyebrow">Диаграмма</p>
                  <h2>Круговая разбивка категорий</h2>
                </div>
                <div className="pie-chart-grid">
                  {Object.entries(categoryGroups).map(([currency, rows]) => (
                    <CategoryPieChart key={currency} currency={currency} rows={rows} />
                  ))}
                </div>
              </section>

              <section className="card analytics-card analytics-timeline-card">
                <div className="card-header">
                  <p className="eyebrow">Динамика</p>
                  <h2>{analytics.timeline_granularity === 'month' ? 'По месяцам' : 'По дням'}</h2>
                </div>
                <div className="timeline-grid">
                  {Object.entries(timelineGroups).map(([currency, rows]) => (
                    <div className="timeline-currency" key={currency}>
                      <h3>{currency}</h3>
                      <div className="table-scroll">
                        <table className="analytics-table">
                          <thead>
                            <tr>
                              <th>Дата</th>
                              <th>Доход</th>
                              <th>Расход</th>
                              <th>Баланс</th>
                            </tr>
                          </thead>
                          <tbody>
                            {rows.map((row) => (
                              <tr key={`${row.date}-${row.currency}`}>
                                <td>{row.date}</td>
                                <td>{toMoney(row.income, row.currency)}</td>
                                <td>{toMoney(row.expense, row.currency)}</td>
                                <td>{toMoney(row.balance, row.currency)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}
        </>
      )}
    </section>
  );
};

export default AnalyticsDashboard;
