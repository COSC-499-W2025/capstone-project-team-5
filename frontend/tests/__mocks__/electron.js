module.exports = {
  contextBridge: {
    exposeInMainWorld: (key, api) => {
      global[key] = api;
    },
  },
};