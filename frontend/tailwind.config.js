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
      colors: {
        primary: '#ff6b6b',
        secondary: '#4ecdc4',
        dark: '#1a1a2e',
        accent: '#e94560',
      },
    },
  },
  plugins: [],
}
