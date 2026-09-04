import { apiClient } from './api/apiClient';

// The backend resolves the development identity from this header.  Keeping it
// here makes every workbench request explicit about its acting annotator.
const optionsFor = (userId) => ({ headers: { 'X-User-Id': userId } });

export const annotationService = {
  listBatches: () => apiClient.get('/annotations/batches'),
  getTasks: (userId, batchId) => apiClient.get('/annotations/tasks', { batch_id: batchId }, optionsFor(userId)),
  getTask: (userId, taskId) => apiClient.get(`/annotations/tasks/${taskId}`, {}, optionsFor(userId)),
  saveDraft: (userId, taskId, data) => apiClient.post(`/annotations/tasks/${taskId}/draft`, data, optionsFor(userId)),
  submit: (userId, taskId, data) => apiClient.post(`/annotations/tasks/${taskId}/submit`, data, optionsFor(userId)),
  taxonomy: () => apiClient.get('/annotations/taxonomy'),
  quality: (batchId) => apiClient.get('/annotations/quality', { batch_id: batchId }),
  releaseReadiness: (batchId) => apiClient.get('/annotations/release-readiness', { batch_id: batchId }),
  disagreements: (userId, batchId) => apiClient.get('/annotations/disagreements', { batch_id: batchId }, optionsFor(userId)),
  disagreement: (userId, taskId) => apiClient.get(`/annotations/disagreements/${taskId}`, {}, optionsFor(userId)),
  adjudicate: (userId, taskId, data) => apiClient.post(`/annotations/disagreements/${taskId}/adjudicate`, data, optionsFor(userId)),
  seedDemo: (userId) => apiClient.post('/annotations/demo-seed', {}, optionsFor(userId)),
};
