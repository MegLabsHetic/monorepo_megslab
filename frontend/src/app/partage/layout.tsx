import type { Metadata } from "next";
import type { ReactNode } from "react";

/**
 * Un lien de partage circule : colle dans un ticket public, un canal indexe ou
 * transmis en referrer, il devient atteignable par un robot. La page rend les
 * chiffres du client et, via "Voir le SQL", les noms de ses tables : sans ce
 * noindex, la promesse de ne rien reveler de l'espace ne tient pas.
 */
export const metadata: Metadata = {
  robots: { index: false, follow: false, nocache: true },
};

export default function LayoutPartage({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
