import api from './api';

export const reportService = {
  list: (params: Record<string, any>) => api.get('/reports', { params }),
  getDetail: (id: number) => api.get(`/reports/${id}`),
  upload: (sessionId: number, file: File) => {
    const formData = new FormData();
    formData.append('session_id', sessionId.toString());
    formData.append('file', file);
    return api.post('/reports/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  sign: (id: number) => api.post(`/reports/${id}/sign`),
  download: (id: number) => api.get(`/reports/${id}/download`, { responseType: 'blob' }),
};
