import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

export const login = async (credentials) => {
  const response = await apiClient.post('/auth/login/', credentials);
  return response.data;
};

export const register = async (credentials) => {
  const response = await apiClient.post('/auth/register/', credentials);
  return response.data;
};

export const logout = async () => {
  await apiClient.post('/auth/logout/');
};

export const fetchCategories = async () => {
  try {
    const response = await apiClient.get('/categories/');
    return response.data;
  } catch (error) {
    console.error('Error fetching categories:', error);
    throw error;
  }
};

export const fetchStatements = async (filters = {}) => {
  try {
    const response = await apiClient.get('/statements/', { params: filters });
    return response.data;
  } catch (error) {
    console.error('Error fetching statements:', error);
    throw error;
  }
};

export const updateStatement = async (statementId, statement) => {
  const response = await apiClient.patch(`/statements/${statementId}/`, statement);
  return response.data;
};

export const deleteStatement = async (statementId) => {
  await apiClient.delete(`/statements/${statementId}/`);
};

export const fetchAnalytics = async (filters = {}) => {
  const response = await apiClient.get('/analytics/', { params: filters });
  return response.data;
};

export const createCategory = async (title) => {
  const response = await apiClient.post('/categories/', { title });
  return response.data;
};

export const importStatements = async (file, schema) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('schema', JSON.stringify(schema));

  const response = await apiClient.post('/import/statements/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const importManualStatements = async (rows) => {
  const response = await apiClient.post('/import/manual/', { rows });
  return response.data;
};

export const previewImportStatements = async (file, schema) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('schema', JSON.stringify(schema));

  const response = await apiClient.post('/import/preview/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const fetchImportTemplates = async () => {
  const response = await apiClient.get('/import/templates/');
  return response.data;
};

export const createImportTemplate = async (template) => {
  const response = await apiClient.post('/import/templates/', template);
  return response.data;
};

export const updateImportTemplate = async (templateId, template) => {
  const response = await apiClient.patch(`/import/templates/${templateId}/`, template);
  return response.data;
};
