/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bankPrimary: "#3b82f6",
        bankAccent: "#60a5fa",
        bankBg: "#0b0f19",
        bankSurface: "#161b26",
        bankBorder: "#1e293b",
        riskCritical: "#ef4444",
        riskHigh: "#f97316",
        riskMedium: "#f59e0b",
        riskLow: "#10b981",
      },
    },
  },
  plugins: [],
};
