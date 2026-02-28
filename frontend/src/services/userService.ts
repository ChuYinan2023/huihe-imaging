import api from './api';

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  phone?: string;
  is_active: boolean;
}

export const userService = {
  list: (page = 1, pageSize = 20) =>
    api.get('/users', { params: { page, page_size: pageSize } }),
  create: (data: { username: string; email: string; password: string; full_name: string; role: string; phone?: string }) =>
    api.post('/users', data),
  update: (id: number, data: Partial<User>) =>
    api.put(`/users/${id}`, data),
  resetPassword: (id: number) =>
    api.put(`/users/${id}/reset-password`),
};
