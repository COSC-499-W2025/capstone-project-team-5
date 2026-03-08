// Mock Electron's contextBridge so preload.js can be imported in Node
jest.mock('electron', () => ({
  contextBridge: {
    exposeInMainWorld: jest.fn((key, api) => {
      global[key] = api;
    }),
  },
}));

// Polyfill fetch for Node
global.fetch = jest.fn();