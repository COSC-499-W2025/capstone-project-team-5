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
        'zippy-bounce': 'zippyBounce 0.5s cubic-bezier(0.34,1.56,0.64,1) forwards',
        'zippy-wobble': 'zippyWobble 2.5s ease-in-out infinite',
        'zippy-wave': 'zippyWave 0.6s ease-in-out infinite',

        'zippy-hop': 'zippyHop 2s ease-in-out infinite',
        'zippy-excited': 'zippyExcited 0.4s ease-in-out infinite',
        'zippy-point': 'zippyPoint 0.5s ease-out forwards',
        'clippy-exit': 'clippyExit 1s ease-in forwards',
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
        zippyBounce: {
          from: { opacity: 0, transform: 'scale(0.3) translateY(20px)' },
          to:   { opacity: 1, transform: 'scale(1) translateY(0)' },
        },
        zippyWobble: {
          '0%, 100%': { transform: 'rotate(0deg)' },
          '25%':      { transform: 'rotate(-3deg)' },
          '75%':      { transform: 'rotate(3deg)' },
        },
        zippyWave: {
          '0%, 100%': { transform: 'rotate(0deg)' },
          '50%':      { transform: 'rotate(-20deg)' },
        },

        zippyHop: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-4px)' },
        },
        zippyExcited: {
          '0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
          '50%':      { transform: 'translateY(-3px) rotate(2deg)' },
        },
        zippyPoint: {
          from: { transform: 'rotate(0deg)' },
          to:   { transform: 'rotate(-30deg)' },
        },
        clippyExit: {
          from: { opacity: 1, transform: 'translateX(0) rotate(0deg)' },
          to:   { opacity: 0, transform: 'translateX(300px) rotate(45deg)' },
        },
      },
    },
  },
  plugins: [],
}