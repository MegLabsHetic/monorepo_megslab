import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * L'image de production ne contient que le serveur et ses dependances reelles,
   * pas les 400 Mo de node_modules : Next trace ce qui est vraiment importe et
   * l'assemble dans .next/standalone.
   */
  output: "standalone",
};

export default nextConfig;
