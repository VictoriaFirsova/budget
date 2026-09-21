import React, { useEffect, useState } from 'react';
import { fetchCategories } from '../../api';

const FilterForm = ({ onFilter }) => {
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState({
    search: '',
    category: '',
    currency: '',
    card: '',
    date_from: '',
    date_to: '',
  });

  useEffect(() => {
    const loadCategories = async () => {
      try {
        setCategories(await fetchCategories());
      } catch (error) {
        console.error('Error fetching filter categories:', error);
      }
    };

    loadCategories();
  }, []);

  const updateFilter = (fieldName, value) => {
    setFilters((currentFilters) => ({
      ...currentFilters,
      [fieldName]: value,
    }));
  };

  const compactFilters = (nextFilters) => Object.fromEntries(
    Object.entries(nextFilters).filter(([, value]) => value !== ''),
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    onFilter(compactFilters(filters));
  };

  const handleReset = () => {
    const emptyFilters = {
      search: '',
      category: '',
      currency: '',
      card: '',
      date_from: '',
      date_to: '',
    };
    setFilters(emptyFilters);
    onFilter({});
  };

  return (
    <form className="filter-card" onSubmit={handleSubmit}>
      <label>
        Поиск
        <input
          className={!filters.search ? 'empty-control' : ''}
          type="text"
          placeholder="Описание, категория, карта..."
          value={filters.search}
          onChange={(e) => updateFilter('search', e.target.value)}
        />
      </label>

      <label>
        Категория
        <select
          className={!filters.category ? 'empty-control' : ''}
          value={filters.category}
          onChange={(e) => updateFilter('category', e.target.value)}
        >
          <option value="">Все категории</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.title}
            </option>
          ))}
        </select>
      </label>

      <label>
        Валюта
        <input
          className={!filters.currency ? 'empty-control' : ''}
          type="text"
          maxLength="3"
          placeholder="USD"
          value={filters.currency}
          onChange={(e) => updateFilter('currency', e.target.value.toUpperCase())}
        />
      </label>

      <label>
        Карта/счет
        <input
          className={!filters.card ? 'empty-control' : ''}
          type="text"
          placeholder="Visa, TBC..."
          value={filters.card}
          onChange={(e) => updateFilter('card', e.target.value)}
        />
      </label>

      <label>
        Дата от
        <input
          className={!filters.date_from ? 'empty-control' : ''}
          type="date"
          value={filters.date_from}
          onChange={(e) => updateFilter('date_from', e.target.value)}
        />
      </label>

      <label>
        Дата до
        <input
          className={!filters.date_to ? 'empty-control' : ''}
          type="date"
          value={filters.date_to}
          onChange={(e) => updateFilter('date_to', e.target.value)}
        />
      </label>

      <div className="filter-actions">
        <button type="submit">Применить</button>
        <button className="secondary-button" type="button" onClick={handleReset}>
          Сбросить
        </button>
      </div>
    </form>
  );
};

export default FilterForm;
