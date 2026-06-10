const { app, BrowserWindow } = require('electron')
const path = require('path')

const configs = [
  { platform: 'bilibili', roomId: '102' },
  { platform: 'douyin', roomId: '888' },
  { platform: 'kuaishou', roomId: '666' },
]

app.whenReady().then(() => {
  configs.forEach(({ platform, roomId }) => {
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
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
