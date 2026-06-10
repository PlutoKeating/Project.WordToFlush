import { WordPuzzle } from '@shared/types/game'

const puzzles: WordPuzzle[] = [
  {
    id: 'p001',
    word: '笔记本',
    wordLength: 3,
    category: '学习用品',
    difficulty: 'easy',
    hints: ['学生常用', '可以写字', '便携'],
  },
  {
    id: 'p002',
    word: '铅笔盒',
    wordLength: 3,
    category: '学习用品',
    difficulty: 'easy',
    hints: ['方形', '收纳文具', '带拉链'],
  },
  {
    id: 'p003',
    word: '橡皮擦',
    wordLength: 3,
    category: '学习用品',
    difficulty: 'easy',
    hints: ['消除痕迹', '白色', '软软的'],
  },
  {
    id: 'p004',
    word: '火锅',
    wordLength: 2,
    category: '美食',
    difficulty: 'easy',
    hints: ['热气腾腾', '多人共享', '麻辣'],
  },
  {
    id: 'p005',
    word: '珍珠奶茶',
    wordLength: 4,
    category: '美食',
    difficulty: 'medium',
    hints: ['有吸管', '甜甜的', '黑色颗粒'],
  },
  {
    id: 'p006',
    word: '手机壳',
    wordLength: 3,
    category: '数码',
    difficulty: 'easy',
    hints: ['保护作用', '各种图案', '塑料材质'],
  },
  {
    id: 'p007',
    word: '蓝牙耳机',
    wordLength: 4,
    category: '数码',
    difficulty: 'medium',
    hints: ['无线', '戴在耳朵上', '听音乐'],
  },
  {
    id: 'p008',
    word: '画蛇添足',
    wordLength: 4,
    category: '成语',
    difficulty: 'hard',
    hints: ['多此一举', '动物', '四条腿'],
  },
  {
    id: 'p009',
    word: '掩耳盗铃',
    wordLength: 4,
    category: '成语',
    difficulty: 'hard',
    hints: ['自欺欺人', '声音', '偷东西'],
  },
  {
    id: 'p010',
    word: '对牛弹琴',
    wordLength: 4,
    category: '成语',
    difficulty: 'medium',
    hints: ['浪费口舌', '动物', '乐器'],
  },
]

export class WordPuzzleRepository {
  random(): WordPuzzle {
    const index = Math.floor(Math.random() * puzzles.length)
    return { ...puzzles[index] }
  }

  getByCategory(category: string): WordPuzzle[] {
    return puzzles.filter((p) => p.category === category).map((p) => ({ ...p }))
  }
}
