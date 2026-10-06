"use client";

import { useEffect, useState } from "react";

import { BarreBudget } from "@/components/finops/barreBudget";
import { useSession, useTraduireErreur } from "@/components/session/contexteSession";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type EtatBudget, api } from "@/lib/api";

/**
 * Le budget mensuel de l'assistant : montant, seuil d'alerte, blocage. Le
 * controle est fait par le serveur avant chaque question ; ici on ne fait
 * que le regler et montrer ou on en est.
 */
export function SectionBudget({ peutModifier }: { peutModifier: boolean }) {
  const { jeton } = useSession();
  const traduireErreur = useTraduireErreur();
  const [etat, setEtat] = useState<EtatBudget | null>(null);
  const [montant, setMontant] = useState("");
  const [seuil, setSeuil] = useState("80");
  const [bloquant, setBloquant] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api
      .budget(jeton)
      .then((e) => {
        setEtat(e);
        setMontant(e.budget_dollars === null ? "" : String(e.budget_dollars));
        setSeuil(String(e.seuil_alerte_pct));
        setBloquant(e.bloquant);
      })
      .catch((probleme) => setErreur(traduireErreur(probleme)));
  }, [jeton, traduireErreur]);

  const enregistrer = async (evenement: React.FormEvent) => {
    evenement.preventDefault();
    setErreur(null);
    setMessage(null);
    try {
      const nouvel = await api.definirBudget(jeton, {
        budget_dollars: montant.trim() === "" ? null : Number(montant),
        seuil_alerte_pct: Number(seuil),
        bloquant,
      });
      setEtat(nouvel);
      setMessage(nouvel.budget_dollars === null ? "Budget retire." : "Budget enregistre.");
    } catch (probleme) {
      setErreur(traduireErreur(probleme));
    }
  };

  return (
    <section className="space-y-4" aria-labelledby="titre-budget">
      <h2 id="titre-budget" className="font-display text-sm uppercase tracking-widest text-muted">
        Budget de l&apos;assistant
      </h2>
      <form
        onSubmit={enregistrer}
        className="space-y-5 rounded-xl border border-line bg-surface p-5 shadow-carte lg:max-w-xl"
      >
        {etat && <BarreBudget etat={etat} />}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="budget">Budget mensuel, en dollars</Label>
            <Input
              id="budget"
              type="number"
              min={0}
              step="0.01"
              placeholder="Aucun"
              value={montant}
              onChange={(e) => setMontant(e.target.value)}
              disabled={!peutModifier}
            />
          </div>
          <div>
            <Label htmlFor="seuil">Alerte a partir de, en %</Label>
            <Input
              id="seuil"
              type="number"
              min={1}
              max={100}
              value={seuil}
              onChange={(e) => setSeuil(e.target.value)}
              disabled={!peutModifier}
            />
          </div>
        </div>
        <label className="flex items-start gap-3 text-sm text-text">
          <input
            type="checkbox"
            className="mt-1"
            checked={bloquant}
            onChange={(e) => setBloquant(e.target.checked)}
            disabled={!peutModifier}
          />
          <span>
            Bloquer les questions une fois le budget atteint.
            <span className="block text-xs text-muted">
              Sinon, l&apos;assistant continue de repondre et l&apos;alerte reste affichee.
            </span>
          </span>
        </label>
        {erreur && <Alert>{erreur}</Alert>}
        {message && <p className="text-sm text-succes">{message}</p>}
        {peutModifier && (
          <Button type="submit" className="w-auto px-5">
            Enregistrer
          </Button>
        )}
      </form>
    </section>
  );
}
