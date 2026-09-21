import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { login } from '../../api';

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await login({ username, password });
      onLogin(response.user);
      navigate('/dashboard');
    } catch (error) {
      setErrorMessage('Неверное имя пользователя или пароль');
    }
  };

  return (
    <main className="auth-page">
      <section className="card auth-card">
        <p className="eyebrow">Welcome back</p>
        <h2>Вход</h2>
        <form onSubmit={handleLogin}>
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

          <label>Пароль</label>
          <input
            type="password"
            name="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit">Войти</button>
          {errorMessage && <p className="alert">{errorMessage}</p>}
        </form>
        <p className="muted-text">
          Еще нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </section>
    </main>
  );
};

export default Login;
