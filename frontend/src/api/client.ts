import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Добавляем токен к запросам
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Обработка ошибок
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: async (data: { name: string; email: string }) => {
    const response = await apiClient.post('/auth/register', data);
    return response.data;
  },

  login: async (data: { email: string }) => {
    const response = await apiClient.post('/auth/login', data);
    return response.data;
  },

  me: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },
};

// Bots API
export const botsApi = {
  getTemplates: async () => {
    const response = await apiClient.get('/bots/templates');
    return response.data;
  },

  create: async (data: { bot_type: string; config: Record<string, unknown> }) => {
    const response = await apiClient.post('/bots/create', data);
    return response.data;
  },

  list: async () => {
    const response = await apiClient.get('/bots/');
    return response.data;
  },

  get: async (botId: string) => {
    const response = await apiClient.get(`/bots/${botId}`);
    return response.data;
  },

  updateConfig: async (botId: string, config: Record<string, unknown>) => {
    const response = await apiClient.patch(`/bots/${botId}/config`, config);
    return response.data;
  },

  deploy: async (botId: string) => {
    const response = await apiClient.post(`/bots/${botId}/deploy`);
    return response.data;
  },

  delete: async (botId: string) => {
    const response = await apiClient.delete(`/bots/${botId}`);
    return response.data;
  },
};

export type BotTemplate = {
  type: string;
  name: string;
  description: string;
  config_schema: {
    fields: Array<{
      name: string;
      label: string;
      type: string;
      required?: boolean;
      default?: string;
      placeholder?: string;
      description?: string;
      options?: Array<{ value: string; label: string }>;
    }>;
    integrations?: Array<{
      id: string;
      name: string;
      description: string;
    }>;
  };
};

export type Bot = {
  id: string;
  bot_type: string;
  bot_name: string;
  bot_token?: string;
  bot_username?: string;
  config: Record<string, unknown>;
  status: 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'DELETED';
  created_at: string;
  updated_at: string;
};

export type User = {
  tenant_id: string;
  slug: string;
  name: string;
  email: string;
  status: string;
};
