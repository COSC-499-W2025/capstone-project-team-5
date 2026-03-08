const { app, BrowserWindow } = require('electron');
const path = require('path');

async function waitForVite(retries = 20, delay = 500) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch('http://localhost:5173');
      if (res.ok) return;
    } catch (_) {}
    await new Promise(r => setTimeout(r, delay));
  }
}

async function waitForApi(retries = 30, delay = 500) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch('http://localhost:8000/health');
      if (res.ok) return;
    } catch (_) {}
    await new Promise(r => setTimeout(r, delay));
  }
}

async function createWindow() {
  const isDev = process.env.NODE_ENV !== 'production';

  await Promise.all([
    waitForApi(),
    isDev ? waitForVite() : Promise.resolve(),
  ]);

  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 900,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0d0f12',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    win.loadURL('http://localhost:5173');
    win.webContents.openDevTools();          // auto-open devtools in dev
  } else {
    win.loadFile(path.join(__dirname, '../dist/renderer/index.html'));
  }
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });