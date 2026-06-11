/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{vue,ts,js}',
  ],
  theme: {
    extend: {
      aspectRatio: {
        '9/16': '9 / 16',
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', '"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      colors: {
        'cyber-bg':      '#F0F0F5',
        'cyber-surface': '#FFFFFF',
        'cyber-panel':   '#F5F5FA',
        'cyber-hover':   '#EAEAF2',

        'neon-pink':   '#FF2D7F',
        'neon-cyan':   '#00D4E0',
        'neon-purple': '#9B59B6',
        'neon-yellow': '#FFB800',
        'neon-green':  '#00E676',
        'neon-orange': '#FF6B35',

        'ink-dark':  '#1A1A2E',
        'ink-gray':  '#555570',
        'ink-muted': '#8888A0',

        'edge-light': '#D8D8E8',
        'edge-glow':  '#C8C8E0',
      },
      fontSize: {
        'xs':   ['1.5rem',  { lineHeight: '2rem' }],
        'sm':   ['1.75rem', { lineHeight: '2.25rem' }],
        'base': ['2rem',    { lineHeight: '2.5rem' }],
        'lg':   ['2.25rem', { lineHeight: '2.75rem' }],
        'xl':   ['2.5rem',  { lineHeight: '3rem' }],
        '2xl':  ['3rem',    { lineHeight: '3.5rem' }],
        '3xl':  ['3.75rem', { lineHeight: '4rem' }],
        '4xl':  ['4.5rem',  { lineHeight: '5rem' }],
        '5xl':  ['6rem',    { lineHeight: '1' }],
        '6xl':  ['7.5rem',  { lineHeight: '1' }],
        '7xl':  ['9rem',    { lineHeight: '1' }],
      },
      borderRadius: {
        'card': '0.75rem',
        'btn':  '0.5rem',
      },
      boxShadow: {
        'neon-pink':   '0 0 12px rgba(255, 45, 127, 0.25)',
        'neon-cyan':   '0 0 12px rgba(0, 212, 224, 0.25)',
        'neon-purple': '0 0 12px rgba(155, 89, 182, 0.25)',
        'neon-green':  '0 0 12px rgba(0, 230, 118, 0.25)',
        'card':        '0 2px 8px rgba(26, 26, 46, 0.05)',
        'card-lg':     '0 4px 16px rgba(26, 26, 46, 0.08)',
      },
    },
  },
  plugins: [],
}
