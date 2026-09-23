// 由 word_data/*.json 组成题库；新增分类需在此登记
import c0 from './data/word_data/交通工具.json'
import c1 from './data/word_data/动物.json'
import c2 from './data/word_data/品质.json'
import c3 from './data/word_data/地理地貌.json'
import c4 from './data/word_data/天体.json'
import c5 from './data/word_data/娱乐活动.json'
import c6 from './data/word_data/季节.json'
import c7 from './data/word_data/学习用品.json'
import c8 from './data/word_data/数码产品.json'
import c9 from './data/word_data/植物.json'
import c10 from './data/word_data/气象活动.json'
import c11 from './data/word_data/美食.json'
import c12 from './data/word_data/职业.json'
import c13 from './data/word_data/运动项目.json'

export interface Puzzle {
  id: string
  word: string
  wordLength: number
  category: string
  difficulty: 'easy' | 'medium' | 'hard'
}
const ALL: Puzzle[] = [...c0, ...c1, ...c2, ...c3, ...c4, ...c5, ...c6, ...c7, ...c8, ...c9, ...c10, ...c11, ...c12, ...c13, ] as Puzzle[]

export function randomPuzzle(exclude: { category?: string; ids?: string[] } = {}): Puzzle {
  let pool = ALL.filter((p) => p.category !== exclude.category && !exclude.ids?.includes(p.id))
  if (pool.length === 0) pool = ALL
  return pool[Math.floor(Math.random() * pool.length)]
}
