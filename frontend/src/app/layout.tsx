import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

const espaceGrotesk = Space_Grotesk({ variable: "--font-display", subsets: ["latin"] });
const inter = Inter({ variable: "--font-body", subsets: ["latin"] });
const jetbrainsMono = JetBrains_Mono({ variable: "--font-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MegsLab",
  description: "Vos donnees, comprises. Connectez vos sources, explorez-les, decidez.",
  applicationName: "MegsLab",
  icons: {
    icon: [{ url: "/marque/logo.png", type: "image/png" }],
    apple: [{ url: "/marque/logo.png", type: "image/png" }],
    shortcut: "/marque/logo.png",
  },
  appleWebApp: {
    title: "MegsLab",
    capable: true,
  },
  openGraph: {
    title: "MegsLab",
    description: "Vos donnees, comprises. Connectez vos sources, explorez-les, decidez.",
    images: ["/marque/logo.png"],
  },
};

/**
 * Applique le theme choisi avant le premier rendu. Sans ce script, la page
 * s'afficherait en clair puis basculerait en sombre sous les yeux de qui a
 * choisi le sombre.
 */
const SCRIPT_THEME = `
try {
  var t = localStorage.getItem("megslab_theme");
  if (t === "sombre") document.documentElement.dataset.theme = "sombre";
} catch (e) {}
`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_THEME }} />
      </head>
      <body
        className={`${espaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
