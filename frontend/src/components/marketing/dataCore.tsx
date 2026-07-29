"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

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
    const nombrePoints = 180;
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
    const animer = () => {
      groupe.rotation.x += (cibleX - groupe.rotation.x) * 0.05;
      groupe.rotation.y += (cibleY - groupe.rotation.y + (reduireMouvement ? 0 : 0.003)) * 0.05;
      renderer.render(scene, camera);
      idAnimation = requestAnimationFrame(animer);
    };
    animer();

    return () => {
      cancelAnimationFrame(idAnimation);
      observateur.disconnect();
      conteneur.removeEventListener("pointermove", surDeplacement);
      conteneur.removeChild(renderer.domElement);
      filaire.geometry.dispose();
      (filaire.material as THREE.Material).dispose();
      geometriePoints.dispose();
      (points.material as THREE.Material).dispose();
      renderer.dispose();
    };
  }, []);

  return <div ref={conteneurRef} className="h-full w-full" aria-hidden="true" />;
}
