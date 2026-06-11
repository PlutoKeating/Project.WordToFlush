export type Platform = 'bilibili' | 'douyin' | 'kuaishou'

export type Difficulty = 'easy' | 'medium' | 'hard'

export interface WordPuzzle {
  id: string
  word: string
  wordLength: number
  category: string
  difficulty: Difficulty
}

export interface GuessRecord {
  userId: string
  userName: string
  guess: string
  affinity: number
  timestamp: number
}

export interface Player {
  userId: string
  userName: string
  totalScore: number
  currentScore: number
  guessCount: number
}

export interface RoomState {
  roomId: string
  platform: Platform
  currentPuzzle: WordPuzzle | null
  streak: number
  highestAffinity: number
  guessBoard: GuessRecord[]
  leaderboard: Player[]
  previousPuzzle: string | null
  solvedBy: string | null
  revealedChars: boolean[]
}

export interface RoomConfig {
  roomId: string
  platform: Platform
  autoNextDelay: number
}

export interface PuzzleSolvedEvent {
  word: string
  solvedBy: string
}

export interface SocketEvents {
  'room:join': { roomId: string; platform: Platform; clientId: string }
  'room:leave': { roomId: string }
  'game:newPuzzle': WordPuzzle
  'game:guess': { roomId: string; userId: string; userName: string; guess: string; clientId: string }
  'game:guessResult': GuessRecord
  'game:state': RoomState
  'game:leaderboard': Player[]
  'game:previousPuzzle': string
  'game:puzzleSolved': PuzzleSolvedEvent
}
