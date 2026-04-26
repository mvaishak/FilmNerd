/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#000000',
        'background-alt': '#09090b',
        border: '#27272a',
      },
      fontFamily: {
        sans: ['var(--font-geist-sans)'],
        mono: ['var(--font-geist-mono)'],
      },
      transitionDuration: {
        DEFAULT: '0ms',
      },
    },
  },
  plugins: [],
}
