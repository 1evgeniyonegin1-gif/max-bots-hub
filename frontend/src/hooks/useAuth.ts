import { create } from 'zustand';
import { authApi, type User } from '../api/client';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string) => Promise<void>;
  register: (name: string, email: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email: string) => {
    try {
      const response = await authApi.login({ email });
      localStorage.setItem('access_token', response.access_token);
      set({
        user: {
          tenant_id: response.tenant_id,
          slug: response.tenant_slug,
          name: response.tenant_slug,
          email: email,
          status: 'ACTIVE',
        },
        isAuthenticated: true,
      });
    } catch (error) {
      localStorage.removeItem('access_token');
      throw error;
    }
  },

  register: async (name: string, email: string) => {
    try {
      const response = await authApi.register({ name, email });
      localStorage.setItem('access_token', response.access_token);
      set({
        user: {
          tenant_id: response.tenant_id,
          slug: response.tenant_slug,
          name: name,
          email: email,
          status: 'TRIAL',
        },
        isAuthenticated: true,
      });
    } catch (error) {
      localStorage.removeItem('access_token');
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isLoading: false, isAuthenticated: false });
      return;
    }

    try {
      const user = await authApi.me();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      localStorage.removeItem('access_token');
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
