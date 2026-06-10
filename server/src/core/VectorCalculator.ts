import axios from 'axios'

const EMBEDDING_CACHE_MAX = 500

export class VectorCalculator {
  private host: string
  private model: string
  private embeddingCache: Map<string, number[]> = new Map()
  private affinityCache: Map<string, number> = new Map()

  constructor() {
    this.host = process.env.OLLAMA_HOST || 'http://localhost:11434'
    this.model = process.env.OLLAMA_MODEL || 'bge-large-zh'
  }

  private cacheKey(guess: string, target: string): string {
    return `${guess}::${target}`
  }

  async getEmbedding(text: string): Promise<number[]> {
    const cached = this.embeddingCache.get(text)
    if (cached) return cached

    const response = await axios.post(`${this.host}/api/embeddings`, {
      model: this.model,
      prompt: text,
    })
    const embedding: number[] = response.data.embedding

    if (this.embeddingCache.size >= EMBEDDING_CACHE_MAX) {
      const oldest = this.embeddingCache.keys().next().value as string
      this.embeddingCache.delete(oldest)
    }
    this.embeddingCache.set(text, embedding)

    return embedding
  }

  cosineSimilarity(vecA: number[], vecB: number[]): number {
    const dotProduct = vecA.reduce((sum, a, i) => sum + a * vecB[i], 0)
    const normA = Math.sqrt(vecA.reduce((sum, a) => sum + a * a, 0))
    const normB = Math.sqrt(vecB.reduce((sum, b) => sum + b * b, 0))
    return dotProduct / (normA * normB)
  }

  async calculateAffinity(guess: string, target: string): Promise<number> {
    if (guess === target) return 1.0

    const key = this.cacheKey(guess, target)
    const cached = this.affinityCache.get(key)
    if (cached !== undefined) return cached

    const vecA = await this.getEmbedding(guess)
    const vecB = await this.getEmbedding(target)
    const sim = this.cosineSimilarity(vecA, vecB)
    const result = Math.max(0, Math.min(1, sim))

    if (this.affinityCache.size >= EMBEDDING_CACHE_MAX) {
      const oldest = this.affinityCache.keys().next().value as string
      this.affinityCache.delete(oldest)
    }
    this.affinityCache.set(key, result)

    return result
  }
}
