/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./renderer/index.html",
    "./renderer/src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:        '#0a0b0d',
        surface:   '#111318',
        elevated:  '#181b22',
        border:    '#1e2229',
        'border-hi': '#2c3140',
        accent:    '#f5a623',
        'accent-dim': '#c4841a',
        'accent-muted': 'rgba(245,166,35,0.1)',
        ink:       '#dde3ee',
        muted:     '#4e5668',
        success:   '#3dd68c',
        danger:    '#f25656',
      },
      fontFamily: {
        sans: ['Cabinet Grotesk', 'sans-serif'],
        mono: ['Geist Mono', 'monospace'],
      },
      fontSize: {
        '2xs': ['10px', { lineHeight: '1.4', letterSpacing: '0.06em' }],
      },
      borderRadius: {
        DEFAULT: '8px',
        lg: '12px',
      },
      animation: {
        'fade-up': 'fadeUp 0.2s ease forwards',
        'pulse-dot': 'pulseDot 2s ease-in-out infinite',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: 0, transform: 'translateY(8px)' },
          to:   { opacity: 1, transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%, 100%': { opacity: 1 },
          '50%':      { opacity: 0.4 },
        },
      },
    },
  },
  plugins: [],
}