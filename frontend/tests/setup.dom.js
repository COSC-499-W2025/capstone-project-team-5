// Mock window.api (the contextBridge surface) so React components
// can call it without a real Electron environment.
global.window = global.window ?? {};

global.window.api = {
  health:               jest.fn().mockResolvedValue({ status: 'ok' }),
  getCurrentUser:       jest.fn().mockResolvedValue({ username: 'testuser' }),
  setUsername:          jest.fn(),
  setAuthUsername:      jest.fn(),
  getUsername:          jest.fn().mockReturnValue(null),
  getProjects:          jest.fn().mockResolvedValue([]),
  getSkills:            jest.fn().mockResolvedValue([]),
  getProfile:           jest.fn().mockResolvedValue(null),
  getWorkExperiences:   jest.fn().mockResolvedValue([]),
  getEducations:        jest.fn().mockResolvedValue([]),
  createWorkExperience:  jest.fn().mockResolvedValue({}),
  updateWorkExperience:  jest.fn().mockResolvedValue({}),
  deleteWorkExperience:  jest.fn().mockResolvedValue(null),
  getResumes:           jest.fn().mockResolvedValue([]),
  createResume:         jest.fn().mockResolvedValue({}),
  updateResume:         jest.fn().mockResolvedValue({}),
  deleteResume:         jest.fn().mockResolvedValue(null),
  analyzeProject:       jest.fn().mockResolvedValue({}),
  uploadProjectThumbnail: jest.fn().mockResolvedValue(null),
  deleteProjectThumbnail: jest.fn().mockResolvedValue(null),
  getProjectThumbnailUrl: jest.fn((id) => `http://localhost:8000/api/projects/${id}/thumbnail`),
  getLLMConfig:         jest.fn().mockResolvedValue({ is_allowed: false, model_preferences: [] }),
  downloadResumePdf:    jest.fn().mockResolvedValue({
    bytes: new ArrayBuffer(8),
    contentType: 'application/pdf',
    filename: 'resume.pdf',
  }),

  // Consent
  getAvailableServices: jest.fn().mockResolvedValue([
    { service_name: 'openai',    display_name: 'OpenAI',    description: 'GPT models' },
    { service_name: 'anthropic', display_name: 'Anthropic', description: 'Claude models' },
  ]),
  getLatestConsent:     jest.fn().mockResolvedValue(null),
  giveConsent:          jest.fn().mockResolvedValue({ status: 'ok' }),
  getLLMConfig:         jest.fn().mockResolvedValue({ provider: 'openai' }),
};
