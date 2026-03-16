module.exports = {
  GlobalWorkerOptions: { workerSrc: '' },
  getDocument: jest.fn(() => ({
    promise: Promise.resolve({
      numPages: 0,
      getPage: jest.fn(),
      destroy: jest.fn(),
    }),
  })),
}
