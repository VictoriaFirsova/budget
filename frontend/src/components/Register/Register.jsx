import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register } from '../../api';

const Register = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const response = await register({ username, email, password });
      onLogin(response.user);
      navigate('/dashboard');
    } catch (error) {
      setErrorMessage(error.response?.data?.detail || 'Не удалось зарегистрироваться');
    }
  };

  return (
    <main className="auth-page">
      <section className="card auth-card">
        <p className="eyebrow">Create account</p>
        <h2>Регистрация</h2>
        <form onSubmit={handleRegister}>
          <label>Имя пользователя</label>
          <input
            type="text"
            placeholder="Имя пользователя"
            aria-label="Имя пользователя"
            name="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />

          <label>Email</label>
          <input
            type="email"
            name="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <label>Пароль</label>
          <input
            type="password"
            name="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit">Зарегистрироваться</button>
          {errorMessage && <p className="alert">{errorMessage}</p>}
        </form>
        <p className="muted-text">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </section>
    </main>
  );
};

export default Register;
