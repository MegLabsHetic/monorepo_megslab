"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

/** Degrade radial blanc->transparent : la base d'un halo lumineux en sprite additif. */
function _texturelueur(): THREE.Texture {
  const taille = 128;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = taille;
  const contexte = canvas.getContext("2d")!;
  const degrade = contexte.createRadialGradient(
    taille / 2,
    taille / 2,
    0,
    taille / 2,
    taille / 2,
    taille / 2
  );
  degrade.addColorStop(0, "rgba(255,255,255,1)");
  degrade.addColorStop(0.4, "rgba(255,255,255,0.5)");
  degrade.addColorStop(1, "rgba(255,255,255,0)");
  contexte.fillStyle = degrade;
  contexte.fillRect(0, 0, taille, taille);
  return new THREE.CanvasTexture(canvas);
}

/**
 * Le "Data Core" : un losange filaire avec un nuage de points, tournant
 * lentement, qui reagit legerement au curseur. Composant isole expres (brief) :
 * il ne connait rien du reste de la page, juste un canvas a remplir.
 */
export function DataCore() {
  const conteneurRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const conteneur = conteneurRef.current;
    if (!conteneur) return;

    const reduireMouvement = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    camera.position.z = 6;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    conteneur.appendChild(renderer.domElement);

    const groupe = new THREE.Group();
    scene.add(groupe);

    // Le losange : un octaedre, arete visible seulement (pas de faces pleines).
    const geometrieLosange = new THREE.OctahedronGeometry(2, 0);
    const filaire = new THREE.LineSegments(
      new THREE.EdgesGeometry(geometrieLosange),
      new THREE.LineBasicMaterial({ color: 0x3fbfae, transparent: true, opacity: 0.8 })
    );
    groupe.add(filaire);

    // Le nuage de points : des donnees dispersees autour du losange.
    const nombrePoints = 220;
    const positions = new Float32Array(nombrePoints * 3);
    for (let i = 0; i < nombrePoints; i++) {
      const rayon = 2.6 + Math.random() * 1.4;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      positions[i * 3] = rayon * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = rayon * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = rayon * Math.cos(phi);
    }
    const geometriePoints = new THREE.BufferGeometry();
    geometriePoints.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const points = new THREE.Points(
      geometriePoints,
      new THREE.PointsMaterial({ color: 0x3fbfae, size: 0.035, transparent: true, opacity: 0.5 })
    );
    groupe.add(points);

    // Des noeuds lumineux aux 6 sommets du losange (rayon 2, comme la geometrie
    // ci-dessus) : un halo degrade en sprite additif, pas une vraie lumiere
    // Three.js — le materiau du filaire ne reagit pas a l'eclairage, une
    // PointLight resterait donc invisible ici.
    const RAYON_LOSANGE = 2;
    const positionsSommets: [number, number, number][] = [
      [RAYON_LOSANGE, 0, 0],
      [-RAYON_LOSANGE, 0, 0],
      [0, RAYON_LOSANGE, 0],
      [0, -RAYON_LOSANGE, 0],
      [0, 0, RAYON_LOSANGE],
      [0, 0, -RAYON_LOSANGE],
    ];
    const texture = _texturelueur();
    const halos = positionsSommets.map(([x, y, z]) => {
      const halo = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: texture,
          color: 0x5fe0c8,
          transparent: true,
          opacity: 0.85,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        })
      );
      halo.position.set(x, y, z);
      halo.scale.setScalar(0.9);
      groupe.add(halo);
      return halo;
    });

    let cibleX = 0;
    let cibleY = 0;

    const surDeplacement = (evenement: PointerEvent) => {
      const rect = conteneur.getBoundingClientRect();
      cibleX = ((evenement.clientY - rect.top) / rect.height - 0.5) * 0.4;
      cibleY = ((evenement.clientX - rect.left) / rect.width - 0.5) * 0.6;
    };
    conteneur.addEventListener("pointermove", surDeplacement);

    const redimensionner = () => {
      const { width, height } = conteneur.getBoundingClientRect();
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    redimensionner();
    const observateur = new ResizeObserver(redimensionner);
    observateur.observe(conteneur);

    let idAnimation: number;
    const animer = (temps: number) => {
      groupe.rotation.x += (cibleX - groupe.rotation.x) * 0.05;
      groupe.rotation.y += (cibleY - groupe.rotation.y + (reduireMouvement ? 0 : 0.003)) * 0.05;

      if (!reduireMouvement) {
        halos.forEach((halo, i) => {
          const pulsation = 0.75 + 0.25 * Math.sin(temps / 900 + i * 1.3);
          halo.scale.setScalar(0.7 + pulsation * 0.35);
          (halo.material as THREE.SpriteMaterial).opacity = 0.5 + pulsation * 0.4;
        });
      }

      renderer.render(scene, camera);
      idAnimation = requestAnimationFrame(animer);
    };
    idAnimation = requestAnimationFrame(animer);

    return () => {
      cancelAnimationFrame(idAnimation);
      observateur.disconnect();
      conteneur.removeEventListener("pointermove", surDeplacement);
      conteneur.removeChild(renderer.domElement);
      filaire.geometry.dispose();
      (filaire.material as THREE.Material).dispose();
      geometriePoints.dispose();
      (points.material as THREE.Material).dispose();
      texture.dispose();
      halos.forEach((halo) => (halo.material as THREE.Material).dispose());
      renderer.dispose();
    };
  }, []);

  return <div ref={conteneurRef} className="h-full w-full" aria-hidden="true" />;
}
