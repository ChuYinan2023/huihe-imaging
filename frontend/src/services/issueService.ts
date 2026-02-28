import api from './api';

export const issueService = {
  list: (params: Record<string, any>) => api.get('/issues', { params }),
  getDetail: (id: number) => api.get(`/issues/${id}`),
  create: (data: { session_id: number; description: string }) => api.post('/issues', data),
  process: (id: number, content: string) => api.put(`/issues/${id}/process`, { content }),
  review: (id: number, action: 'approve' | 'reject', content?: string) => api.put(`/issues/${id}/review`, { action, content }),
};
