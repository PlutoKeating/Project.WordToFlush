const { app, BrowserWindow } = require('electron')
const path = require('path')

const args = process.argv.slice(2)
const platform = args.find((a) => a.startsWith('--platform='))?.split('=')[1] || 'bilibili'
const roomId = args.find((a) => a.startsWith('--roomId='))?.split('=')[1] || '102'

function createWindow() {
  const win = new BrowserWindow({
    width: 480,
    height: 854,
    title: `WordToFlush-${platform.toUpperCase()}-${roomId}`,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  const url = `http://localhost:3000/?platform=${platform}&roomId=${roomId}`
  win.loadURL(url)
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
