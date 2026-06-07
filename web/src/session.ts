const STORAGE_KEY = "catan-client-id";

let cached: string | null = null;

/**
 * A random id minted once per browser and persisted in localStorage. Sent on
 * every API request so the server can scope "my games" to this browser
 * without any login — clearing storage / a new browser simply starts a fresh,
 * empty lobby.
 */
export function getClientId(): string {
  if (cached) return cached;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      cached = stored;
      return cached;
    }
    const id = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, id);
    cached = id;
  } catch {
    // Storage unavailable (e.g. private browsing): fall back to an
    // in-memory id for the lifetime of this page load.
    cached = crypto.randomUUID();
  }
  return cached;
}
