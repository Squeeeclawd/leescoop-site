import { openSavedPlans, SAVED_PLANS_KEY } from './savedPlans';

let savedOnly = false;
const status = document.getElementById('action-status');
const announce = (message: string) => { if (status) status.textContent = message; };
const saved = openSavedPlans(announce);
function renderSaved() {
  document.querySelectorAll<HTMLButtonElement>('[data-save]').forEach(button => {
    const active = saved.has(button.dataset.save!);
    button.setAttribute('aria-pressed', String(active));
    button.textContent = active ? 'Saved ✓' : 'Save';
  });
  let count = 0;
  let hasMatches = false;
  document.querySelectorAll<HTMLElement>('.discovery-card').forEach(card => {
    const excluded = savedOnly && !saved.has(card.dataset.slug!);
    card.classList.toggle('not-saved', excluded);
    if (!card.hidden) {
      hasMatches = true;
      if (!excluded) count++;
    }
  });
  const empty = document.getElementById('saved-empty');
  if (empty) empty.hidden = !savedOnly || count > 0 || !hasMatches;
  const result = document.getElementById('feed-result');
  if (result) result.textContent = savedOnly ? `${count} saved ${count === 1 ? 'item' : 'items'} · this browser` : result.getAttribute('data-base-text') ?? result.textContent;
}
renderSaved();
document.addEventListener('leescoop:filtered', renderSaved);
window.addEventListener('storage', event => { if (event.key === SAVED_PLANS_KEY || event.key === null) { saved.sync(); renderSaved(); } });
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
    const added = saved.toggle(slug);
    if (saved.persistent) announce(added ? 'Saved on this browser.' : 'Removed from saved.');
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
