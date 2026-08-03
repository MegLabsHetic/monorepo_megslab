/**
 * Boutons Google / Microsoft presents dans l'interface mais desactives : le
 * flux OAuth cote backend n'existe pas encore. Mieux vaut le dire explicitement
 * (titre + etiquette) que laisser un bouton qui ne ferait rien silencieusement.
 */
export function SocialAuthButtons() {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <button
          type="button"
          disabled
          title="Bientot disponible"
          className="flex h-10 flex-1 cursor-not-allowed items-center justify-center gap-2 rounded-md border border-line bg-surface-2 text-sm text-muted opacity-50"
        >
          <IconeGoogle />
          Google
        </button>
        <button
          type="button"
          disabled
          title="Bientot disponible"
          className="flex h-10 flex-1 cursor-not-allowed items-center justify-center gap-2 rounded-md border border-line bg-surface-2 text-sm text-muted opacity-50"
        >
          <IconeMicrosoft />
          Microsoft
        </button>
      </div>
      <p className="text-center text-xs text-muted">Connexion Google/Microsoft bientot disponible</p>

      <div className="my-2 flex items-center gap-3">
        <span className="h-px flex-1 bg-line" />
        <span className="text-xs uppercase text-muted">ou</span>
        <span className="h-px flex-1 bg-line" />
      </div>
    </div>
  );
}

function IconeGoogle() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.99.66-2.25 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.85A11 11 0 0 0 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09A6.6 6.6 0 0 1 5.5 12c0-.73.13-1.43.34-2.09V7.06H2.18A11 11 0 0 0 1 12c0 1.77.43 3.45 1.18 4.94z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1a11 11 0 0 0-9.82 6.06l3.66 2.85C6.71 7.31 9.14 5.38 12 5.38z"
      />
    </svg>
  );
}

function IconeMicrosoft() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <rect x="1" y="1" width="10" height="10" fill="#F35325" />
      <rect x="13" y="1" width="10" height="10" fill="#81BC06" />
      <rect x="1" y="13" width="10" height="10" fill="#05A6F0" />
      <rect x="13" y="13" width="10" height="10" fill="#FFBA08" />
    </svg>
  );
}
