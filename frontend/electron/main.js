const { app, BrowserWindow } = require('electron')

function createWindow() {
  const win = new BrowserWindow({
    width: 480,
    height: 854,
    title: 'WordToFlush',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  const url = 'http://localhost:3000/'
  win.loadURL(url)
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
