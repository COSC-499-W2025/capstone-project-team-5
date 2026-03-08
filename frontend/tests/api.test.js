const mockJson = (data, ok = true) =>
  Promise.resolve({
    ok,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data))
  });

beforeEach(() => {
  jest.resetModules();
  global.fetch = jest.fn();

  // Mock contextBridge to expose api globally
  jest.mock('electron', () => ({
    contextBridge: {
      exposeInMainWorld: (name, api) => {
        global[name] = api;
      }
    }
  }));

  require('../src/preload.js');
});

describe('api.health', () => {
  it('returns ok when API is up', async () => {
    fetch.mockResolvedValue(mockJson({ status: 'ok' }));

    const result = await global.api.health();

    expect(result).toEqual({ status: 'ok' });
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/health', {"headers": {"Content-Type": "application/json"}, "method": "GET"});
  });
});

describe('api.getCurrentUser', () => {
  it('calls GET /api/users/me', async () => {
    fetch.mockResolvedValue(mockJson({ username: 'alice' }));

    const user = await global.api.getCurrentUser();

    expect(user.username).toBe('alice');
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/users/me',
      expect.objectContaining({ method: 'GET' })
    );
  });
});

describe('api.getProjects', () => {
  it('calls GET /api/projects/', async () => {
    fetch.mockResolvedValue(mockJson([{ id: 1, name: 'Portfolio Site' }]));

    const projects = await global.api.getProjects();

    expect(projects).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/projects/',
      expect.objectContaining({ method: 'GET' })
    );
  });
});

describe('api.getSkills', () => {
  it('calls GET /api/skills/', async () => {
    fetch.mockResolvedValue(mockJson([{ name: 'Python' }]));

    const skills = await global.api.getSkills();

    expect(skills[0].name).toBe('Python');
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/skills/',
      expect.objectContaining({ method: 'GET' })
    );
  });
});

describe('api.getPortfolioByUser', () => {
  it('calls GET /api/portfolio/user/{username}', async () => {
    fetch.mockResolvedValue(mockJson({ id: 10 }));

    const portfolio = await global.api.getPortfolioByUser('alice');

    expect(portfolio.id).toBe(10);
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/portfolio/user/alice',
      expect.objectContaining({ method: 'GET' })
    );
  });
});

describe('api.getWorkExperiences', () => {
  it('calls GET /api/users/{username}/work-experiences', async () => {
    fetch.mockResolvedValue(mockJson([{ company: 'Google' }]));

    const work = await global.api.getWorkExperiences('alice');

    expect(work[0].company).toBe('Google');
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/users/alice/work-experiences',
      expect.objectContaining({ method: 'GET' })
    );
  });
});

describe('error handling', () => {
  it('throws on non-ok response', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve('Not found')
    });

    await expect(global.api.getProjects()).rejects.toThrow('Not found');
  });

  it('throws on network failure', async () => {
    fetch.mockRejectedValue(new Error('ECONNREFUSED'));

    await expect(global.api.getProjects()).rejects.toThrow('ECONNREFUSED');
  });
});