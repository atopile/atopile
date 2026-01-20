/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'agent-running': '#22c55e',
        'agent-completed': '#3b82f6',
        'agent-failed': '#ef4444',
        'agent-terminated': '#f59e0b',
        'agent-pending': '#6b7280',
      },
    },
  },
  plugins: [],
}
