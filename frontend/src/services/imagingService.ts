import api from './api';

export const imagingService = {
  createSession: (data: { project_id: number; center_id: number; subject_id: number; visit_point: string; imaging_type: string }) =>
    api.post('/imaging/sessions', data),
  uploadFile: (sessionId: number, file: File, onProgress?: (percent: number) => void) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/imaging/sessions/${sessionId}/upload`, formData, {
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    });
  },
  completeSession: (sessionId: number) =>
    api.post(`/imaging/sessions/${sessionId}/complete`),
  list: (params: Record<string, any>) =>
    api.get('/imaging', { params }),
  listBySubject: (params: Record<string, any>) =>
    api.get('/imaging/by-subject', { params }),
  getDetail: (id: number) =>
    api.get(`/imaging/${id}`),
  getThumbnail: (fileId: number) =>
    api.get(`/imaging/files/${fileId}/thumbnail`, { responseType: 'blob' }),
  downloadFile: (fileId: number) =>
    api.get(`/imaging/files/${fileId}/download`, { responseType: 'blob' }),
};
