import axios from 'axios'

export class VectorCalculator {
  private host: string
  private model: string

  constructor() {
    this.host = process.env.OLLAMA_HOST || 'http://localhost:11434'
    this.model = process.env.OLLAMA_MODEL || 'bge-large-zh'
  }

  async getEmbedding(text: string): Promise<number[]> {
    const response = await axios.post(`${this.host}/api/embeddings`, {
      model: this.model,
      prompt: text,
    })
    return response.data.embedding
  }

  cosineSimilarity(vecA: number[], vecB: number[]): number {
    const dotProduct = vecA.reduce((sum, a, i) => sum + a * vecB[i], 0)
    const normA = Math.sqrt(vecA.reduce((sum, a) => sum + a * a, 0))
    const normB = Math.sqrt(vecB.reduce((sum, b) => sum + b * b, 0))
    return dotProduct / (normA * normB)
  }

  async calculateAffinity(guess: string, target: string): Promise<number> {
    if (guess === target) return 1.0

    const vecA = await this.getEmbedding(guess)
    const vecB = await this.getEmbedding(target)
    const sim = this.cosineSimilarity(vecA, vecB)

    return Math.max(0, Math.min(1, sim))
  }
}
