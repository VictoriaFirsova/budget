import React, { useState } from 'react';
import { BrowserRouter as Router, NavLink, Route, Routes, Navigate } from 'react-router-dom';
import './App.css';
import Header from './components/Header/Header';
import FilterForm from './components/FilterForm/FilterForm';
import DataTable from './components/DataTable/DataTable';
import FileUpload from './components/FileUpload/FileUpload';
import CategoryEditor from './components/CategoryEditor/CategoryEditor';
import AnalyticsDashboard from './components/AnalyticsDashboard/AnalyticsDashboard';
import Login from './components/Login/Login';
import Register from './components/Register/Register';
import { logout } from './api';

const getStoredUser = () => {
  try {
    const storedUser = window.localStorage.getItem('budgetUser');
    return storedUser ? JSON.parse(storedUser) : null;
  } catch (error) {
    return null;
  }
};

const AppLayout = ({ children, onLogout }) => (
  <main className="dashboard-page">
    <Header />
    <div className="dashboard-shell">
      <div className="session-bar">
        <span>Вы вошли в приложение</span>
        <div className="app-nav">
          <NavLink to="/dashboard">Операции</NavLink>
          <NavLink to="/analytics">Дашборды</NavLink>
        </div>
        <button className="secondary-button" type="button" onClick={onLogout}>
          Выйти
        </button>
      </div>
      {children}
    </div>
  </main>
);

const Dashboard = () => {
  const [filters, setFilters] = useState({});
  const [refreshKey, setRefreshKey] = useState(0);

  const refreshStatements = () => {
    setRefreshKey((currentKey) => currentKey + 1);
  };

  return (
    <>
      <div className="dashboard-grid dashboard-grid-top">
        <FileUpload onImportComplete={refreshStatements} />
        <CategoryEditor />
      </div>
      <FilterForm onFilter={setFilters} />
      <DataTable filters={filters} refreshKey={refreshKey} />
    </>
  );
};

const App = () => {
  const [user, setUser] = useState(getStoredUser);

  const handleLogin = (nextUser) => {
    window.localStorage.setItem('budgetUser', JSON.stringify(nextUser));
    setUser(nextUser);
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      window.localStorage.removeItem('budgetUser');
      setUser(null);
    }
  };

  return (
    <Router>
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/dashboard" /> : <Login onLogin={handleLogin} />}
        />
        <Route
          path="/register"
          element={user ? <Navigate to="/dashboard" /> : <Register onLogin={handleLogin} />}
        />
        <Route
          path="/dashboard"
          element={(
            user
              ? (
                <AppLayout onLogout={handleLogout}>
                  <Dashboard />
                </AppLayout>
              )
              : <Navigate to="/login" />
          )}
        />
        <Route
          path="/analytics"
          element={(
            user
              ? (
                <AppLayout onLogout={handleLogout}>
                  <AnalyticsDashboard />
                </AppLayout>
              )
              : <Navigate to="/login" />
          )}
        />
        <Route path="/" element={<Navigate to="/dashboard" />} />
      </Routes>
    </Router>
  );
};

export default App;
