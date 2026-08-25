/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        bg: 'rgb(var(--color-bg) / <alpha-value>)',
        surface: 'rgb(var(--color-surface) / <alpha-value>)',
        ink: 'rgb(var(--color-ink) / <alpha-value>)',
        tea: 'rgb(var(--color-tea) / <alpha-value>)',
        muted: 'rgb(var(--color-muted) / <alpha-value>)',
        accent: 'rgb(var(--color-accent) / <alpha-value>)',
        'accent-bright': 'rgb(var(--color-accent-bright) / <alpha-value>)',
        'accent-tint': 'rgb(var(--color-accent-tint) / <alpha-value>)',
        'on-accent': 'rgb(var(--color-on-accent) / <alpha-value>)',
        alert: 'rgb(var(--color-alert) / <alpha-value>)',
      },
      fontFamily: {
        serif: ['"Palatino Linotype"', 'Palatino', '"Noto Serif TC"', 'Georgia', 'serif'],
        sans: [
          '-apple-system',
          '"Segoe UI"',
          'Roboto',
          '"PingFang TC"',
          '"Microsoft JhengHei"',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
}
