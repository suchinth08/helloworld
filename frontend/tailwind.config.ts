import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Slate palette for dark/light mode
        background: {
          light: "#f8fafc", // slate-50
          dark: "#0f172a",  // slate-900
        },
        surface: {
          light: "#ffffff",
          dark: "#1e293b",  // slate-800
        },
        border: {
          light: "#e2e8f0", // slate-200
          dark: "#334155",  // slate-700
        },
      },
    },
  },
  plugins: [],
};

export default config;
