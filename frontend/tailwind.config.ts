import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        accent: "var(--accent)",
        text: "var(--text)",
        muted: "var(--muted)",
        line: "var(--line)",
      },
      fontFamily: {
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      // Deux durees seulement : 140 ms pour un retour immediat (survol, focus),
      // 280 ms pour un changement de mise en page (depliage, apparition).
      transitionDuration: {
        140: "140ms",
        280: "280ms",
      },
      keyframes: {
        apparition: {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        balayage: {
          from: { transform: "translateX(-100%)" },
          to: { transform: "translateX(300%)" },
        },
      },
      animation: {
        apparition: "apparition 280ms ease-out",
        balayage: "balayage 1.6s ease-in-out infinite",
      },
    },
  },
};

export default config;
