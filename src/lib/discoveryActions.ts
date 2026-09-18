const storageKey = 'leescoop:saved:v1';
let saved = new Set<string>();
let savedOnly = false;
const status = document.getElementById('action-status');
const announce = (message: string) => { if (status) status.textContent = message; };
function readSaved() {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(storageKey) || '[]');
    saved = new Set(Array.isArray(value) ? value.filter((x): x is string => typeof x === 'string').slice(0, 1000) : []);
  } catch { announce('Browser storage unavailable. Saves will last for this visit only.'); }
}
function renderSaved() {
  document.querySelectorAll<HTMLButtonElement>('[data-save]').forEach(button => {
    const active = saved.has(button.dataset.save!);
    button.setAttribute('aria-pressed', String(active));
    button.textContent = active ? 'Saved ✓' : 'Save';
  });
  let count = 0;
  document.querySelectorAll<HTMLElement>('.discovery-card').forEach(card => {
    const excluded = savedOnly && !saved.has(card.dataset.slug!);
    card.classList.toggle('not-saved', excluded);
    if (!card.hidden && !excluded) count++;
  });
  const empty = document.getElementById('saved-empty');
  if (empty) empty.hidden = !savedOnly || count > 0;
  const result = document.getElementById('feed-result');
  if (result) result.textContent = savedOnly ? `${count} saved ${count === 1 ? 'item' : 'items'} · this browser` : result.getAttribute('data-base-text') ?? result.textContent;
}
readSaved();
renderSaved();
document.addEventListener('leescoop:filtered', renderSaved);
window.addEventListener('storage', event => { if (event.key === storageKey || event.key === null) { readSaved(); renderSaved(); } });
document.getElementById('saved-filter')?.addEventListener('click', event => {
  savedOnly = !savedOnly;
  (event.currentTarget as HTMLElement).setAttribute('aria-pressed', String(savedOnly));
  renderSaved();
});
document.getElementById('filter-clear-all')?.addEventListener('click', () => {
  savedOnly = false;
  document.getElementById('saved-filter')?.setAttribute('aria-pressed', 'false');
  renderSaved();
});
document.addEventListener('click', async event => {
  if (!(event.target instanceof Element)) return;
  const save = event.target.closest<HTMLButtonElement>('[data-save]');
  if (save) {
    const slug = save.dataset.save!;
    saved.has(slug) ? saved.delete(slug) : saved.add(slug);
    try { localStorage.setItem(storageKey, JSON.stringify([...saved])); announce(saved.has(slug) ? 'Saved on this browser.' : 'Removed from saved.'); }
    catch { announce('Storage unavailable or full. Your change is saved for this visit only.'); }
    renderSaved();
  }
  const share = event.target.closest<HTMLButtonElement>('[data-share]');
  if (!share) return;
  const url = new URL(share.dataset.share!, location.origin).href;
  try {
    if (navigator.share) { await navigator.share({title: share.dataset.title, url}); return; }
    if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(url); announce('Link copied.'); return; }
  } catch (error) { if (error instanceof Error && error.name === 'AbortError') return; }
  // Copy remains possible when native sharing and clipboard permissions are unavailable.
  if (status) {
    status.textContent = 'Copy this link: ';
    const input = document.createElement('input');
    input.value = url; input.readOnly = true; input.setAttribute('aria-label', 'Link to share');
    status.append(input); input.focus(); input.select();
  }
});

export {};
