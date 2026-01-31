/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'graph-bg': '#1a1a2e',
        'panel-bg': '#16213e',
        'panel-border': '#0f3460',
        'accent': '#e94560',
        'text-primary': '#eaeaea',
        'text-secondary': '#a0a0a0',
      },
    },
  },
  plugins: [],
}
