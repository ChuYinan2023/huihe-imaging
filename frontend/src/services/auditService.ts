import api from './api';

export const auditService = {
  list: (params: Record<string, any>) => api.get('/audit', { params }),
};
