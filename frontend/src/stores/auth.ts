import { create } from 'zustand';
import api, { setTokens, clearTokens } from '../services/api';

interface User {
  id: number;
  username: string;
  full_name: string;
  role: string;
  email: string;
  phone?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  loading: false,

  login: async (username, password) => {
    const res = await api.post('/auth/login', { username, password });
    setTokens(res.data.access_token, res.data.csrf_token);
    set({ user: res.data.user, isAuthenticated: true });
  },

  logout: async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // ignore logout errors
    }
    clearTokens();
    set({ user: null, isAuthenticated: false });
  },

  fetchMe: async () => {
    set({ loading: true });
    try {
      const res = await api.get('/auth/me');
      set({ user: res.data, isAuthenticated: true, loading: false });
    } catch {
      clearTokens();
      set({ user: null, isAuthenticated: false, loading: false });
    }
  },
}));
