import React, { useState, useEffect } from 'react';
import { createCategory, fetchCategories } from '../../api';

const CategoryEditor = () => {
  const [categories, setCategories] = useState([]);
  const [newCategory, setNewCategory] = useState('');

  useEffect(() => {
    const getCategories = async () => {
      try {
        const data = await fetchCategories();
        setCategories(data);
      } catch (error) {
        console.error('Error fetching categories:', error);
      }
    };

    getCategories();
  }, []);

  const handleAddCategory = async () => {
    if (!newCategory) return;

    try {
      const category = await createCategory(newCategory);
      setCategories([...categories, category]);
      setNewCategory('');
    } catch (error) {
      console.error('Error adding category:', error);
    }
  };

  return (
    <section className="card category-card">
      <div className="card-header">
        <p className="eyebrow">Справочник</p>
        <h2>Категории</h2>
      </div>
      <div className="inline-form">
        <input
          type="text"
          placeholder="Новая категория"
          value={newCategory}
          onChange={(e) => setNewCategory(e.target.value)}
        />
        <button type="button" onClick={handleAddCategory}>Добавить</button>
      </div>

      <ul className="pill-list">
        {categories.map(category => (
          <li key={category.id}>{category.title}</li>
        ))}
      </ul>
    </section>
  );
};

export default CategoryEditor;
