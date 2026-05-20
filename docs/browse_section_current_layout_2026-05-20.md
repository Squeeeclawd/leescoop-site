# Browse section current layout notes — 2026-05-20

Purpose: snapshot the current homepage Browse/filter UI before redesign work, so the section can be reverted or compared cleanly.

## Source files

- Markup: `src/pages/index.astro`
- Styling: `src/styles/global.css`
- Current implementation checkpoint before redesign: commit `99f6fcc` (`Refine LeeScoop header navigation`)

## Current markup structure

Homepage section:

```astro
<section class="wrap homepage-section filter-tile panel-glow" id="browse" aria-label="Homepage filters" data-filter-tile>
  <div class="filter-tile-heading">
    <div>
      <p class="eyebrow">Browse</p>
      <h2>Find what matters fastest</h2>
    </div>
    <p>Filter the feed by type, area, or a quick search.</p>
  </div>

  <form class="filter-search-form" id="filter-search-form" action="/search/" method="get">
    <label class="filter-group-label" for="home-filter-input">Search the latest feed</label>
    <div class="filter-search-shell">
      <span class="filter-search-icon" aria-hidden="true">⌕</span>
      <input id="home-filter-input" name="q" type="search" autocomplete="off" placeholder="Search events, news, cities, or venues" />
    </div>
  </form>

  <div class="filter-control-group">
    <p class="filter-group-label" id="filter-type-label">Type</p>
    <div class="content-kind-filter-row" aria-labelledby="filter-type-label">
      <!-- Events / Local News buttons from contentKindStats -->
    </div>
  </div>

  <div class="filter-control-group">
    <p class="filter-group-label" id="filter-area-label">Area</p>
    <div class="filter-tile-pill-row" aria-labelledby="filter-area-label">
      <!-- Area chips from categoryStats -->
    </div>
  </div>

  <div class="filter-tile-footer">
    <button type="button" class="filter-clear-all" id="filter-clear-all" hidden>clear all filters ×</button>
  </div>
</section>
```

## Current visual/layout behavior

- Outer container `.filter-tile`
  - Grid layout with `gap: 0.72rem`
  - `margin-top: 1rem`, `margin-bottom: 1rem`
  - `padding: 0.95rem 1rem 0.82rem`
  - Background: `linear-gradient(180deg, rgba(7, 80, 111, 0.58), rgba(6, 58, 82, 0.66))`
  - Border: `1px solid rgba(139, 210, 222, 0.18)`
  - Radius: `1rem`
- Heading row `.filter-tile-heading`
  - Contains eyebrow `Browse`, title `Find what matters fastest`, and right-side explanatory sentence.
- Search
  - Label text above input: `Search the latest feed`
  - Pill-shaped shell with search icon and transparent input.
  - Shell background: `rgba(3, 26, 37, 0.58)`
  - Border: `1px solid rgba(139, 210, 222, 0.2)`
- Primary type filters
  - Label text above row: `Type`
  - Two-column grid via `.content-kind-filter-row`
  - Buttons are large rectangular rounded cards.
  - Background: `linear-gradient(135deg, rgba(139, 210, 222, 0.34), rgba(221, 238, 241, 0.18))`
  - Active/hover shifts toward orange via `rgba(242, 139, 66, ...)`
  - Count appears in dark circular pill on right.
- Area filters
  - Label text above row: `Area`
  - Flexible wrapping pill row via `.filter-tile-pill-row`
  - Pills use teal translucent background, pale text, and count separated by a centered dot.
  - Active area pill uses coral/orange styling.
- Clear button
  - Hidden until filters are active.
  - Sits at bottom-right in `.filter-tile-footer`.

## Design problems called out by Anthony

- Too many explanatory labels make the UI feel cluttered/redundant:
  - `Browse`
  - `Search the latest feed`
  - `Type`
  - `Area`
  - `Filter the feed by type, area, or a quick search.`
- Events and Local News need stronger visual hierarchy.
- Primary feed categories need clearer separation from secondary area/location filters.
- Search should remain prominent but not compete with the category buttons.
- Area filters should feel secondary.

## Revert guidance

If redesign needs to be reverted, restore the `#browse` section markup in `src/pages/index.astro` and the related classes in `src/styles/global.css` from commit `99f6fcc`, specifically:

- `.filter-tile`
- `.filter-tile-heading`
- `.filter-search-form`
- `.filter-search-shell`
- `.filter-search-icon`
- `.filter-control-group`
- `.filter-group-label`
- `.content-kind-filter-row`
- `.content-kind-filter`
- `.filter-tile-pill-row`
- `.filter-tile-pill`
- `.filter-pill-separator`
- `.filter-tile-footer`
- `.filter-clear-all`
