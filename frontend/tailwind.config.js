/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sap: {
          dark: '#0f172a',
          card: '#1e293b',
          border: '#334155',
          brand: '#0284c7',
          success: '#10b981',
          failed: '#ef4444',
          warn: '#f59e0b',
        }
      }
    },
  },
  plugins: [],
}
