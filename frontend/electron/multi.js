const { app, BrowserWindow } = require('electron')

const labels = ['Window-1', 'Window-2', 'Window-3']

app.whenReady().then(() => {
  labels.forEach((label) => {
    const win = new BrowserWindow({
      width: 480,
      height: 854,
      title: `WordToFlush-${label}`,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
      },
    })

    const url = 'http://localhost:3000/'
    win.loadURL(url)
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
