/**
 * Browser-compatible API module for Zip2Job.
 *
 * In Electron, the preload script sets window.api via contextBridge.
 * When running as a plain web app (e.g. on Railway), this module provides
 * the same API surface so React components work identically in both contexts.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

let _token = null;
let _username = null;

function parseResponseBody(res) {
  if (res.status === 204) return null;

  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return res.json();
  }

  return res.text().then((text) => {
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  });
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

function httpError(parsedBody, status) {
  const err = new Error(getErrorMessage(parsedBody, status));
  err.status = status;
  return err;
}

function buildQueryString(params = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    searchParams.set(key, String(value));
  });
  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

function parseFilename(contentDisposition) {
  if (!contentDisposition) return 'resume.pdf';

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1].trim());

  const quotedMatch = contentDisposition.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) return quotedMatch[1].trim();

  const plainMatch = contentDisposition.match(/filename=([^;]+)/i);
  if (plainMatch?.[1]) return plainMatch[1].trim().replace(/^"|"$/g, '');

  return 'resume.pdf';
}

async function request(method, path, body, signal) {
  const headers = { 'Content-Type': 'application/json' };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;

  const opts = { method, headers, signal };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);
  const parsedBody = await parseResponseBody(res);

  if (!res.ok) throw httpError(parsedBody, res.status);
  return parsedBody;
}

async function requestWithForm(method, path, formData, signal) {
  const headers = {};
  if (_token) headers['Authorization'] = `Bearer ${_token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: formData,
    signal,
  });
  const parsedBody = await parseResponseBody(res);

  if (!res.ok) throw httpError(parsedBody, res.status);
  return parsedBody;
}

async function requestBinary(method, path, body, signal) {
  const headers = { 'Content-Type': 'application/json' };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;

  const opts = { method, headers, signal };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);

  if (!res.ok) {
    const parsedBody = await parseResponseBody(res);
    throw httpError(parsedBody, res.status);
  }

  return {
    bytes: await res.arrayBuffer(),
    contentType: res.headers.get('content-type') || 'application/octet-stream',
    filename: parseFilename(res.headers.get('content-disposition')),
  };
}

export const api = {
  // Token management
  setAuthToken:    (token)    => { _token = token || null; },
  getAuthToken:    ()         => _token,

  // Username management
  setAuthUsername: (username) => { _username = (username || '').trim() || null; },
  getAuthUsername: () => _username,
  setUsername:     (username) => { _username = username || null; },
  getUsername:     () => _username,

  clearCredentials: () => { _token = null; _username = null; },

  // Health
  health: () => request('GET', '/health'),

  // Auth
  login:    (data) => request('POST', '/api/auth/login', data),
  register: (data) => request('POST', '/api/auth/register', data),

  // Consent
  getAvailableServices: () => request('GET', '/api/consent/available-services'),
  giveConsent:          (data) => request('POST', '/api/consent', data),
  getLatestConsent:     () => request('GET', '/api/consent/latest'),
  getLLMConfig:         () => request('GET', '/api/consent/llm/config'),

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
  getProjects: (qs = '') =>
    request('GET', `/api/projects/${qs}`),

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

    return requestWithForm('POST', '/api/projects/upload', formData, payload?.signal);
  },

  updateProject: (projectId, data) =>
    request('PATCH', `/api/projects/${projectId}`, data),

  deleteProject: (projectId) =>
    request('DELETE', `/api/projects/${projectId}`),

  // Project thumbnails
  uploadProjectThumbnail: (projectId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return requestWithForm('PUT', `/api/projects/${projectId}/thumbnail`, formData);
  },

  deleteProjectThumbnail: (projectId) =>
    request('DELETE', `/api/projects/${projectId}/thumbnail`),

  getProjectThumbnailUrl: (projectId) =>
    `${API_BASE}/api/projects/${projectId}/thumbnail`,

  getProjectThumbnailObjectUrl: async (projectId, revision = null) => {
    const headers = {};
    if (_token) headers['Authorization'] = `Bearer ${_token}`;

    const query = buildQueryString({ v: revision });
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/thumbnail${query}`, {
      method: 'GET',
      headers,
    });

    if (!res.ok) {
      const parsedBody = await parseResponseBody(res);
      throw httpError(parsedBody, res.status);
    }

    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },

  revokeObjectUrl: (objectUrl) => {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
  },

  // Project analysis
  analyzeProject: (projectId, options = {}) =>
    request(
      'POST',
      `/api/projects/${projectId}/analyze${buildQueryString({
        use_ai: options?.useAi,
        force: options?.force,
      })}`
    ),

  analyzeProjects: (data) =>
    request('POST', '/api/projects/analyze', data),

  rerankProjects: (data) =>
    request('POST', '/api/projects/rerank', data),

  getSavedProjects: (username) =>
    request('GET', `/api/projects/saved/${encodeURIComponent(username)}`),

  updateAnalysis: (projectId, analysisId, data) =>
    request('PATCH', `/api/projects/${projectId}/analyses/${analysisId}`, data),

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

  downloadResumePdf: (username, data) =>
    requestBinary('POST', `/api/users/${username}/resumes/generate`, data),

  createResume: (username, data) =>
    request('POST', `/api/users/${username}/resumes`, data),

  getResume: (username, projectId) =>
    request('GET', `/api/users/${username}/resumes/${projectId}`),

  updateResume: (username, projectId, data) =>
    request('PATCH', `/api/users/${username}/resumes/${projectId}`, data),

  deleteResume: (username, projectId) =>
    request('DELETE', `/api/users/${username}/resumes/${projectId}`),
};
