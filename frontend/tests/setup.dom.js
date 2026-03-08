// Mock window.api (the contextBridge surface) so React components
// can call it without a real Electron environment.
global.window = global.window ?? {};

global.window.api = {
  health:               jest.fn().mockResolvedValue({ status: 'ok' }),
  getCurrentUser:       jest.fn().mockResolvedValue({ username: 'testuser' }),
  getProjects:          jest.fn().mockResolvedValue([]),
  getSkills:            jest.fn().mockResolvedValue([]),
  getWorkExperiences:   jest.fn().mockResolvedValue([]),
  getResumes:           jest.fn().mockResolvedValue([]),

  // Consent
  getAvailableServices: jest.fn().mockResolvedValue([
    { service_name: 'openai',    display_name: 'OpenAI',    description: 'GPT models' },
    { service_name: 'anthropic', display_name: 'Anthropic', description: 'Claude models' },
  ]),
  getLatestConsent:     jest.fn().mockResolvedValue(null),
  giveConsent:          jest.fn().mockResolvedValue({ status: 'ok' }),
  getLLMConfig:         jest.fn().mockResolvedValue({ provider: 'openai' }),
};
