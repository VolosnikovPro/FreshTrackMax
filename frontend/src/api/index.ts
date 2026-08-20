import axios from 'axios';

const api = axios.create({
  baseURL: 'https://partner-sklad.ru:3000/api',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ft_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ft_token');
      localStorage.removeItem('ft_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;

export const authApi = {
  loginMax: (initData: string) => api.post("/auth/max", { initData }),
  login: (username: string, password: string) => api.post('/auth/login', { username, password }),
  seedAdmin: () => api.post('/auth/seed-admin'),
  me: () => api.get('/admin/me'),
};

export const productsApi = {
  list: (activeOnly = true) => api.get('/products/', { params: { active_only: activeOnly } }),
  get: (id: number) => api.get(`/products/${id}`),
  create: (data: object) => api.post('/products/', data),
  update: (id: number, data: object) => api.put(`/products/${id}`, data),
  delete: (id: number) => api.delete(`/products/${id}`),
};

export const batchesApi = {
  list: (params?: object) => api.get('/batches/', { params }),
  get: (id: number) => api.get(`/batches/${id}`),
  expiringUrgent: () => api.get('/batches/expiring/urgent'),
  expiringPlanned: () => api.get('/batches/expiring/planned'),
  create: (data: object) => api.post('/batches/', data),
  update: (id: number, data: object) => api.put(`/batches/${id}`, data),
  delete: (id: number) => api.delete(`/batches/${id}`),
};

export const costsApi = {
  list: (productId?: number) => api.get('/costs/', { params: productId ? { product_id: productId } : {} }),
  create: (data: object) => api.post('/costs/', data),
  update: (id: number, data: object) => api.put(`/costs/${id}`, data),
  delete: (id: number) => api.delete(`/costs/${id}`),
};

export const consumptionApi = {
  list: (params?: object) => api.get('/consumption/', { params }),
  create: (data: object) => api.post('/consumption/', data),
  update: (id: number, data: object) => api.put(`/consumption/${id}`, data),
  delete: (id: number) => api.delete(`/consumption/${id}`),
};

export const headcountApi = {
  list: (params?: object) => api.get('/headcount/', { params }),
  today: () => api.get('/headcount/today'),
  create: (data: object) => api.post('/headcount/', data),
  update: (id: number, data: object) => api.put(`/headcount/${id}`, data),
};

export const adminApi = {
  summary: () => api.get('/admin/summary'),
  listUsers: () => api.get('/admin/users'),
  createUser: (data: object) => api.post('/admin/users', data),
  updateUser: (id: number, data: object) => api.put(`/admin/users/${id}`, data),
  deleteUser: (id: number) => api.delete(`/admin/users/${id}`),
};

export const notificationsApi = {
  triggerUrgent: () => api.post('/notifications/trigger/urgent'),
  triggerPlanned: () => api.post('/notifications/trigger/planned'),
  config: () => api.get('/notifications/config'),
};

export const sitesApi = {
  list: (activeOnly = true) => api.get('/sites/', { params: { active_only: activeOnly } }),
  get: (id: number) => api.get(`/sites/${id}`),
  create: (data: object) => api.post('/sites/', data),
  update: (id: number, data: object) => api.put(`/sites/${id}`, data),
  delete: (id: number) => api.delete(`/sites/${id}`),
};

export const sheetsApi = {
  importFile: (file: File, importType: string) => {
    const form = new FormData();
    form.append('file', file);
    return api.post(`/sheets/import/file?import_type=${importType}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  importSheets: (body: { url_or_id: string; import_type: string; sheet_name?: string }) =>
    api.post('/sheets/import/sheets', body),
  types: () => api.get('/sheets/import/types'),
};

export const consumptionApi = {
  list: (params?: object) => api.get('/consumption/', { params }),
  create: (data: object) => api.post('/consumption/', data),
  update: (id: number, data: object) => api.put(`/consumption/${id}`, data),
  delete: (id: number) => api.delete(`/consumption/${id}`),
  stockCheck: (productId: number, quantity: number) =>
    api.get(`/consumption/stock-check/${productId}`, { params: { quantity } }),
};