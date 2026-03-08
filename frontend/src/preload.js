const { contextBridge } = require('electron');

const API_BASE = 'http://localhost:8000';

async function parseResponseBody(res) {
  if (res.status === 204) return null;

  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return res.json();
  }

  const text = await res.text();
  if (!text) return null;

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function getErrorMessage(parsedBody, status) {
  if (typeof parsedBody === 'string' && parsedBody.trim()) {
    return parsedBody;
  }
  if (parsedBody && typeof parsedBody === 'object' && 'detail' in parsedBody) {
    return typeof parsedBody.detail === 'string'
      ? parsedBody.detail
      : JSON.stringify(parsedBody.detail);
  }
  return `HTTP ${status}`;
}

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };

  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);
  const parsedBody = await parseResponseBody(res);

  if (!res.ok) {
    throw new Error(getErrorMessage(parsedBody, res.status));
  }

  return parsedBody;
}

async function requestWithForm(method, path, formData) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    body: formData,
  });
  const parsedBody = await parseResponseBody(res);

  if (!res.ok) {
    throw new Error(getErrorMessage(parsedBody, res.status));
  }

  return parsedBody;
}

contextBridge.exposeInMainWorld('api', {

  // Health
  health: () => request('GET', '/health'),

  // Consent

  getAvailableServices: () => request('GET', '/api/consent/available-services'),
  giveConsent: (data) => request('POST', '/api/consent', data),
  getLatestConsent: () => request('GET', '/api/consent/latest'),
  getLLMConfig: () => request('GET', '/api/consent/llm/config'),

  // Users
  getCurrentUser: () => request('GET', '/api/users/me'),

  getProfile: (username) =>
    request('GET', `/api/users/${username}/profile`),

  createProfile: (username, data) =>
    request('POST', `/api/users/${username}/profile`, data),

  updateProfile: (username, data) =>
    request('PATCH', `/api/users/${username}/profile`, data),

  // Work Experience
  getWorkExperiences: (username) =>
    request('GET', `/api/users/${username}/work-experiences`),

  createWorkExperience: (username, data) =>
    request('POST', `/api/users/${username}/work-experiences`, data),

  updateWorkExperience: (username, workExpId, data) =>
    request('PATCH', `/api/users/${username}/work-experiences/${workExpId}`, data),

  deleteWorkExperience: (username, workExpId) =>
    request('DELETE', `/api/users/${username}/work-experiences/${workExpId}`),

  // Education
  getEducations: (username) =>
    request('GET', `/api/users/${username}/educations`),

  createEducation: (username, data) =>
    request('POST', `/api/users/${username}/educations`, data),

  updateEducation: (username, educationId, data) =>
    request('PATCH', `/api/users/${username}/educations/${educationId}`, data),

  deleteEducation: (username, educationId) =>
    request('DELETE', `/api/users/${username}/educations/${educationId}`),

  // Projects
  getProjects: () =>
    request('GET', '/api/projects/'),

  getProject: (projectId) =>
    request('GET', `/api/projects/${projectId}`),

  createProjectUpload: (payload) => {
    const fileName = payload?.name || 'upload.zip';
    const contentType = payload?.type || 'application/zip';
    const blob = new Blob([payload?.bytes], { type: contentType });
    const formData = new FormData();
    formData.append('file', blob, fileName);

    if (payload?.projectMapping) {
      formData.append('project_mapping', JSON.stringify(payload.projectMapping));
    }

    return requestWithForm('POST', '/api/projects/upload', formData);
  },

  updateProject: (projectId, data) =>
    request('PATCH', `/api/projects/${projectId}`, data),

  deleteProject: (projectId) =>
    request('DELETE', `/api/projects/${projectId}`),

  // Project analysis
  analyzeProject: (projectId) =>
    request('POST', `/api/projects/${projectId}/analyze`),

  analyzeProjects: (data) =>
    request('POST', '/api/projects/analyze', data),

  rerankProjects: (data) =>
    request('POST', '/api/projects/rerank', data),

  // Project scoring config
  getScoreConfig: () =>
    request('GET', '/api/projects/config/score'),

  updateScoreConfig: (data) =>
    request('PUT', '/api/projects/config/score', data),

  // Project Skills
  getProjectSkills: (projectId) =>
    request('GET', `/api/projects/${projectId}/skills/`),

  getProjectTools: (projectId) =>
    request('GET', `/api/projects/${projectId}/skills/tools`),

  getProjectPractices: (projectId) =>
    request('GET', `/api/projects/${projectId}/skills/practices`),

  getSkills: () =>
    request('GET', '/api/skills/'),


  // Portfolio
  createPortfolio: (data) =>
    request('POST', '/api/portfolio', data),

  getPortfolioByUser: (username) =>
    request('GET', `/api/portfolio/user/${username}`),

  getPortfolio: (portfolioId) =>
    request('GET', `/api/portfolio/${portfolioId}`),

  deletePortfolio: (portfolioId) =>
    request('DELETE', `/api/portfolio/${portfolioId}`),

  addPortfolioItem: (portfolioId, data) =>
    request('POST', `/api/portfolio/${portfolioId}/items`, data),

  createPortfolioItem: (data) =>
    request('POST', '/api/portfolio/items', data),

  // Resumes
  getResumes: (username) =>
    request('GET', `/api/users/${username}/resumes`),

  generateResume: (username, data) =>
    request('POST', `/api/users/${username}/resumes/generate`, data),

  createResume: (username, data) =>
    request('POST', `/api/users/${username}/resumes`, data),

  getResume: (username, projectId) =>
    request('GET', `/api/users/${username}/resumes/${projectId}`),

  updateResume: (username, projectId, data) =>
    request('PATCH', `/api/users/${username}/resumes/${projectId}`, data),

  deleteResume: (username, projectId) =>
    request('DELETE', `/api/users/${username}/resumes/${projectId}`),
});