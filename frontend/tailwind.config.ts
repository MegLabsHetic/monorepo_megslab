import type { Config } from "tailwindcss";

const config: Config = {
  // Pas de darkMode Tailwind : le theme bascule via les variables CSS posees
  // sur [data-theme="sombre"], donc aucune variante dark: n'est necessaire.
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        line: "var(--line)",
        "line-forte": "var(--line-forte)",

        text: "var(--text)",
        "text-doux": "var(--text-doux)",
        muted: "var(--muted)",

        marque: "var(--marque)",
        "marque-forte": "var(--marque-forte)",
        "marque-douce": "var(--marque-douce)",
        "marque-contraste": "var(--marque-contraste)",

        accent: "var(--accent)",
        "accent-doux": "var(--accent-doux)",

        succes: "var(--succes)",
        "succes-doux": "var(--succes-doux)",
        attention: "var(--attention)",
        "attention-doux": "var(--attention-doux)",
        danger: "var(--danger)",
        "danger-doux": "var(--danger-doux)",

        tech: {
          postgres: "var(--tech-postgres)",
          mysql: "var(--tech-mysql)",
          mssql: "var(--tech-mssql)",
          fichier: "var(--tech-fichier)",
        },
      },
      boxShadow: {
        carte: "var(--ombre-carte)",
        relief: "var(--ombre-relief)",
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
          from: { opacity: "0", transform: "translateY(6px)" },
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
