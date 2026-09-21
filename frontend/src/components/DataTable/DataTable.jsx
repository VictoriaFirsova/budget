import React, { useEffect, useState } from 'react';
import {
  deleteStatement,
  fetchCategories,
  fetchStatements,
  updateStatement,
} from '../../api';

const DataTable = ({ filters = {}, refreshKey = 0 }) => {
  const [statements, setStatements] = useState([]);
  const [categories, setCategories] = useState([]);
  const [error, setError] = useState(null);
  const [editingStatementId, setEditingStatementId] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [statementsData, categoriesData] = await Promise.all([
          fetchStatements(filters),
          fetchCategories(),
        ]);
        setStatements(statementsData);
        setCategories(categoriesData);
        setError(null);
      } catch (loadError) {
        console.error('Ошибка при получении данных:', loadError);
        setError('Не удалось загрузить операции и категории.');
      }
    };

    loadData();
  }, [filters, refreshKey]);

  const updateStatementCategory = async (statementId, categoryId) => {
    const nextCategoryId = categoryId ? Number(categoryId) : null;
    setEditingStatementId(statementId);
    try {
      const updatedStatement = await updateStatement(statementId, {
        my_category: nextCategoryId,
      });
      setStatements((currentStatements) => currentStatements.map((statement) => (
        statement.id === statementId ? updatedStatement : statement
      )).filter((statement) => (
        !filters.category || statement.id !== statementId || Number(filters.category) === nextCategoryId
      )));
      setError(null);
    } catch (updateError) {
      console.error('Ошибка при обновлении категории:', updateError);
      setError('Не удалось обновить категорию операции.');
    } finally {
      setEditingStatementId(null);
    }
  };

  const removeStatement = async (statementId) => {
    const shouldDelete = window.confirm('Удалить эту операцию?');
    if (!shouldDelete) {
      return;
    }

    setEditingStatementId(statementId);
    try {
      await deleteStatement(statementId);
      setStatements((currentStatements) => (
        currentStatements.filter((statement) => statement.id !== statementId)
      ));
      setError(null);
    } catch (deleteError) {
      console.error('Ошибка при удалении операции:', deleteError);
      setError('Не удалось удалить операцию.');
    } finally {
      setEditingStatementId(null);
    }
  };

  return (
    <div className="dashboard-grid table-grid">
      <section className="card table-card table-card-wide">
        <div className="card-header">
          <p className="eyebrow">Импортированные данные</p>
          <h2>Операции</h2>
        </div>
        {error && <p className="alert" role="alert">{error}</p>}
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Дата</th>
                <th>Операция</th>
                <th>Сумма</th>
                <th>Валюта</th>
                <th>Категория</th>
                <th>Категория банка</th>
                <th>Карта/счет</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {statements.map(statement => (
                <tr key={statement.id}>
                  <td>{statement.date}</td>
                  <td>{statement.operation_name}</td>
                  <td>{statement.amount}</td>
                  <td>{statement.currency}</td>
                  <td>
                    <select
                      className="table-select"
                      value={statement.my_category || ''}
                      disabled={editingStatementId === statement.id}
                      onChange={(e) => updateStatementCategory(statement.id, e.target.value)}
                    >
                      <option value="">Без категории</option>
                      {categories.map(category => (
                        <option key={category.id} value={category.id}>
                          {category.title}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>{statement.category}</td>
                  <td>{statement.card}</td>
                  <td>
                    <button
                      className="danger-button table-action-button"
                      type="button"
                      disabled={editingStatementId === statement.id}
                      onClick={() => removeStatement(statement.id)}
                    >
                      Удалить
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card table-card categories-table-card">
        <div className="card-header">
          <p className="eyebrow">Список</p>
          <h2>Категории</h2>
        </div>
        <div className="table-scroll categories-table-scroll">
          <table className="categories-table">
            <thead>
              <tr>
                <th>Название</th>
              </tr>
            </thead>
            <tbody>
              {categories.map(category => (
                <tr key={category.id}>
                  <td>{category.title}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default DataTable
