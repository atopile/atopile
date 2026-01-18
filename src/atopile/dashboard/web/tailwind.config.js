/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dashboard-bg': '#0f0f0f',
        'panel-bg': '#1a1a1a',
        'panel-border': '#2a2a2a',
        'accent': '#3b82f6',
        'success': '#22c55e',
        'warning': '#eab308',
        'error': '#ef4444',
        'text-primary': '#f5f5f5',
        'text-secondary': '#a0a0a0',
        'text-muted': '#666666',
      },
    },
  },
  plugins: [],
}
