import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import { createServer } from 'http'
import { Server } from 'socket.io'
import { SessionManager } from './core/SessionManager'
import { GameMaster } from './core/GameMaster'
import { VectorCalculator } from './core/VectorCalculator'
import { SocketHandler } from './websocket/SocketHandler'

const app = express()
const httpServer = createServer(app)
const io = new Server(httpServer, {
  cors: { origin: '*', methods: ['GET', 'POST'] },
})

app.use(cors())
app.use(express.json())

const vectorCalculator = new VectorCalculator()
const gameMaster = new GameMaster(vectorCalculator)
const sessionManager = new SessionManager(gameMaster)
const socketHandler = new SocketHandler(io, sessionManager)

socketHandler.register()

const PORT = process.env.PORT || 8080

httpServer.listen(PORT, () => {
  console.log(`[WordToFlush] Server running on http://localhost:${PORT}`)
})

export { app, io, sessionManager, gameMaster, vectorCalculator }
