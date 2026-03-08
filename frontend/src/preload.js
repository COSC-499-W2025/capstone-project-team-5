const { contextBridge } = require('electron');

const API_BASE = 'http://localhost:8000';

// Username is set once during login/register and reused on every request
let _username = null;

async function request(method, path, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (_username) headers['X-Username'] = _username;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);

  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }

  return res.json();
}

contextBridge.exposeInMainWorld('api', {

  // Internal username state (set after login/register)
  setUsername: (username) => { _username = username; },
  getUsername: () => _username,

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
  getProjects: () =>
    request('GET', '/api/projects/'),

  getProject: (projectId) =>
    request('GET', `/api/projects/${projectId}`),

  createProjectUpload: (data) =>
    request('POST', '/api/projects/upload', data),

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
