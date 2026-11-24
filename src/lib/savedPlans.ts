// Keep the original key so readers' existing homepage bookmarks remain available.
export const SAVED_PLANS_KEY = 'leescoop:saved:v1';

export function openSavedPlans(onStorageError?: (message: string) => void) {
  let saved = new Set<string>();
  // Changes that couldn't be persisted belong to this page until a write succeeds.
  const pending = new Map<string, boolean>();
  let persistent = true;

  function sync() {
    try {
      const value: unknown = JSON.parse(localStorage.getItem(SAVED_PLANS_KEY) ?? '[]');
      if (!Array.isArray(value)) throw new Error('Invalid bookmark list');
      saved = new Set(value.filter((slug): slug is string => typeof slug === 'string' && slug.length > 0));
      for (const [slug, active] of pending) {
        if (active) saved.add(slug);
        else saved.delete(slug);
      }
      persistent = pending.size === 0;
    } catch {
      persistent = false;
      onStorageError?.('Browser storage unavailable. Saves may last for this page only.');
    }
  }

  function change(slug: string, requested?: boolean) {
    sync(); // Include pending edits and any changes already saved on another tab.
    const active = requested ?? !saved.has(slug);
    if (active) saved.add(slug);
    else saved.delete(slug);
    pending.set(slug, active);
    try {
      localStorage.setItem(SAVED_PLANS_KEY, JSON.stringify([...saved]));
      pending.clear();
      persistent = true;
    } catch {
      persistent = false;
      onStorageError?.('Storage unavailable or full. Your change lasts on this page only.');
    }
    window.dispatchEvent(new Event('leescoop:saves-changed'));
    return active;
  }

  sync();
  return {
    sync,
    slugs: () => [...saved],
    has: (slug: string) => saved.has(slug),
    get persistent() { return persistent; },
    toggle: (slug: string) => change(slug),
    add: (slug: string) => change(slug, true),
    remove: (slug: string) => change(slug, false)
  };
}
