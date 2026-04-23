import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export async function uploadFiles(files) {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));
  const { data } = await api.post('/files/upload', formData);
  return data;
}

export async function listFiles() {
  const { data } = await api.get('/files');
  return data;
}

export async function deleteFile(id) {
  await api.delete(`/files/${id}`);
}

export async function listEngines() {
  const { data } = await api.get('/mindmap/engines');
  return data;
}

export async function generateMindmap(fileIds, engine, params) {
  const { data } = await api.post('/mindmap/generate', {
    file_ids: fileIds,
    engine,
    params,
  });
  return data;
}

export function extractErrorMessage(err) {
  if (err.response?.data?.error) {
    const { message, detail } = err.response.data.error;
    return detail ? `${message}: ${detail}` : message;
  }
  if (err.message) return err.message;
  return '发生未知错误';
}
