const mockJson = (data, ok = true) =>
  Promise.resolve({
    ok,
    status: ok ? 200 : 400,
    headers: { get: (key) => key === 'content-type' ? 'application/json' : null },
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data))
  });

const mockBinary = ({ bytes, contentType = 'application/pdf', contentDisposition = 'attachment; filename="resume.pdf"' }) =>
  Promise.resolve({
    ok: true,
    status: 200,
    headers: {
      get: (key) => {
        if (key === 'content-type') return contentType
        if (key === 'content-disposition') return contentDisposition
        return null
      }
    },
    arrayBuffer: () => Promise.resolve(bytes),
    text: () => Promise.resolve(''),
    json: () => Promise.resolve({})
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

describe('api.analyzeProject', () => {
  it('passes optional analysis query params', async () => {
    fetch.mockResolvedValue(mockJson({ id: 7 }));

    await global.api.analyzeProject(7, { useAi: true });

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/projects/7/analyze?use_ai=true',
      expect.objectContaining({ method: 'POST' })
    );
  });
});

describe('api.downloadResumePdf', () => {
  it('returns binary data and filename for resume previews', async () => {
    const bytes = new Uint8Array([1, 2, 3]).buffer;
    fetch.mockResolvedValue(
      mockBinary({
        bytes,
        contentDisposition: 'attachment; filename="alice_resume.pdf"',
      })
    );

    global.api.setAuthUsername('alice');

    const result = await global.api.downloadResumePdf('alice', { template_name: 'modern' });

    expect(result).toEqual({
      bytes,
      contentType: 'application/pdf',
      filename: 'alice_resume.pdf',
    });
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/users/alice/resumes/generate',
      expect.objectContaining({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Username': 'alice',
        },
        body: JSON.stringify({ template_name: 'modern' }),
      })
    );
  });
});

describe('error handling', () => {
  it('throws on non-ok response', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 404,
      headers: { get: (key) => key === 'content-type' ? null : null },
      text: () => Promise.resolve('Not found')
    });

    await expect(global.api.getProjects()).rejects.toThrow('Not found');
  });

  it('throws on network failure', async () => {
    fetch.mockRejectedValue(new Error('ECONNREFUSED'));

    await expect(global.api.getProjects()).rejects.toThrow('ECONNREFUSED');
  });

  it('throws parsed errors for binary resume requests', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 502,
      headers: { get: (key) => key === 'content-type' ? 'application/json' : null },
      json: () => Promise.resolve({ detail: 'LaTeX compiler not found.' }),
      text: () => Promise.resolve(JSON.stringify({ detail: 'LaTeX compiler not found.' }))
    });

    await expect(
      global.api.downloadResumePdf('alice', { template_name: 'jake' })
    ).rejects.toThrow('LaTeX compiler not found.');
  });
});

describe('api.clearCredentials', () => {
  it('resets both getAuthUsername and getUsername to null', () => {
    global.api.setUsername('alice');
    global.api.clearCredentials();
    expect(global.api.getAuthUsername()).toBeNull();
    expect(global.api.getUsername()).toBeNull();
  });

  it('removes X-Username header from subsequent requests after clearing', async () => {
    global.api.setUsername('alice');
    global.api.clearCredentials();

    fetch.mockResolvedValue(mockJson({ status: 'ok' }));
    await global.api.health();

    const calledHeaders = fetch.mock.calls[0][1].headers;
    expect(calledHeaders).not.toHaveProperty('X-Username');
  });
});

describe('api username - unified variable', () => {
  it('setUsername and setAuthUsername write to the same variable', () => {
    global.api.setUsername('alice');
    expect(global.api.getAuthUsername()).toBe('alice');

    global.api.setAuthUsername('bob');
    expect(global.api.getUsername()).toBe('bob');
  });

  it('setUsername is reflected in the X-Username request header', async () => {
    global.api.setUsername('alice');

    fetch.mockResolvedValue(mockJson({ status: 'ok' }));
    await global.api.health();

    expect(fetch.mock.calls[0][1].headers['X-Username']).toBe('alice');
  });
});
