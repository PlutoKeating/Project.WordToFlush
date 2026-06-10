import type { Platform, WordPuzzle, RoomState, GuessRecord } from '@shared/types/game'
import { WordPuzzleRepository } from '../data/WordPuzzleRepository'
import { VectorCalculator } from './VectorCalculator'

export class GameMaster {
  private vectorCalculator: VectorCalculator
  private repository: WordPuzzleRepository

  constructor(vectorCalculator: VectorCalculator) {
    this.vectorCalculator = vectorCalculator
    this.repository = new WordPuzzleRepository()
  }

  async createRoom(roomId: string, platform: Platform): Promise<RoomState> {
    return {
      roomId,
      platform,
      currentPuzzle: null,
      streak: 0,
      starLevel: 0,
      highestAffinity: 0,
      guessBoard: [],
      leaderboard: [],
      previousPuzzle: null,
    }
  }

  async nextPuzzle(roomId: string, roomState: RoomState): Promise<WordPuzzle> {
    if (roomState.currentPuzzle) {
      roomState.previousPuzzle = roomState.currentPuzzle.word
    }

    const puzzle = this.repository.random()
    roomState.currentPuzzle = puzzle
    roomState.guessBoard = []
    roomState.highestAffinity = 0

    return puzzle
  }

  async processGuess(
    roomState: RoomState,
    userId: string,
    userName: string,
    guess: string
  ): Promise<GuessRecord | null> {
    if (!roomState.currentPuzzle) return null

    const affinity = await this.vectorCalculator.calculateAffinity(
      guess,
      roomState.currentPuzzle.word
    )

    if (affinity > roomState.highestAffinity) {
      roomState.highestAffinity = affinity
    }

    const record: GuessRecord = {
      userId,
      userName,
      guess,
      affinity,
      timestamp: Date.now(),
    }

    roomState.guessBoard = [record, ...roomState.guessBoard].slice(0, 20)

    return record
  }
}
