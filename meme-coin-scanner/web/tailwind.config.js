/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        term: {
          bg: "#05080b",
          panel: "#0b1016",
          raised: "#111923",
          line: "#1b2735",
          edge: "#263448",
        },
        neon: {
          DEFAULT: "#00f5a0",
          dim: "#00c47f",
          glow: "#00f5a01a",
        },
        danger: {
          DEFAULT: "#ff4d6d",
          glow: "#ff4d6d1a",
        },
        caution: {
          DEFAULT: "#ffb020",
          glow: "#ffb0201a",
        },
        info: {
          DEFAULT: "#4cc9f0",
          glow: "#4cc9f01a",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: ["Inter Tight", "system-ui", "-apple-system", "sans-serif"],
      },
      keyframes: {
        "slide-in": {
          "0%": { opacity: "0", transform: "translateY(-8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-ring": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.25" },
        },
        sweep: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(400%)" },
        },
        "count-flash": {
          "0%": { color: "#00f5a0" },
          "100%": { color: "inherit" },
        },
      },
      animation: {
        "slide-in": "slide-in 320ms cubic-bezier(0.16, 1, 0.3, 1)",
        "pulse-ring": "pulse-ring 2s ease-in-out infinite",
        sweep: "sweep 2.6s linear infinite",
        "count-flash": "count-flash 700ms ease-out",
      },
    },
  },
  plugins: [],
};
