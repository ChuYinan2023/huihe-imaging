import api from './api';

export const projectService = {
  list: (page = 1, pageSize = 20) =>
    api.get('/projects', { params: { page, page_size: pageSize } }),
  create: (data: { code: string; name: string; description?: string }) =>
    api.post('/projects', data),
  update: (id: number, data: { name?: string; description?: string; status?: string }) =>
    api.put(`/projects/${id}`, data),
  listCenters: (projectId: number) =>
    api.get(`/projects/${projectId}/centers`),
  addCenter: (projectId: number, data: { code: string; name: string }) =>
    api.post(`/projects/${projectId}/centers`, data),
  listSubjects: (projectId: number) =>
    api.get(`/projects/${projectId}/subjects`),
  addSubject: (projectId: number, centerId: number, data: { screening_number: string }) =>
    api.post(`/projects/${projectId}/centers/${centerId}/subjects`, data),
};
