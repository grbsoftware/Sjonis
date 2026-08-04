---
name: ui-suite
description: Build a user interface from the local UI Suite — a token-driven set of layout archetypes and swappable themes (vanilla, blueprint, halo, graphite, oxide, vellum). Use when asked to create, restyle, or scaffold any app UI, dashboard, admin panel, landing page, settings screen, or web front end, or when asked to pick a look for a project, match a brand, or theme an existing interface. Also use when the request mentions the UI suite, an archetype, or a theme by name.
---

# UI Suite

A two-axis system. **Archetype** decides structure and is chosen by what the thing
*is*. **Theme** decides appearance and is chosen by who it is *for*. Any archetype
works with any theme, because archetypes contain no colour, size or typeface — only
tokens the theme fills in.

Suite root: `C:\Users\grben\Design`

```
core/ui.css            structure, primitives, components (no colours)
core/themes.css        six themes, each with a light and a dark palette
core/ui.js             behaviour: dialogs, menus, tabs, sort, validation (optional)
tokens/                same themes as W3C DTCG JSON — portable source
tools/                 build_themes.py: verify | css | gtk | xaml | all
adapters/              tailwind-v4.css, shadcn.css
archetypes/*.html      copyable page scaffolds
dist/                  generated GTK4 CSS and WinUI/WPF XAML
demo/gallery.html      live archetype × theme switcher
```

## Non-web targets

For **Tauri or Electron**, use `core/*.css` unchanged — it is a browser.
For **GTK4 (4.16+)** or **WinUI/WPF**, use `dist/`, regenerating with
`python tools/build_themes.py all`. Run `verify` after any edit to
`core/themes.css` or `tokens/` — it round-trips and reports token loss.

Halo depends on `backdrop-filter` and degrades outside the browser
(compositor-dependent on Linux, unreliable in WebKitGTK). Prefer **blueprint**
for cross-platform work, or give Halo a solid-surface fallback.

Let brand tokens own accent, semantic colour, density and radius; let the OS own
window chrome, native dialogs and scrollbars.

## Tailwind / shadcn

Add `adapters/tailwind-v4.css` or `adapters/shadcn.css` — no dependency enters
the core. shadcn's `--accent` is its hover surface, **not** the brand colour
(`--primary` is); the adapter already handles this, so do not "fix" it.

## Using it

1. **Pick the archetype** by what is being built.
2. **Pick the theme** by audience — see `references/palettes.md`. Say why in one
   sentence, and offer an alternative. Do not silently decide taste on the user's
   behalf.
3. **Copy the archetype file**, link both stylesheets, set `data-theme` and
   optionally `data-mode` on `<html>`.
4. **Tune with token overrides**, never by editing `ui.css`.

```html
<html data-theme="blueprint" data-mode="dark">
<link rel="stylesheet" href="core/ui.css" />
<link rel="stylesheet" href="core/themes.css" />
<body class="ui"> … </body>
```

`class="ui"` is required on the element that should carry the ground and font.

## Behaviour (core/ui.js)

Optional. Add `<script src="core/ui.js"></script>` last and behaviour attaches
itself from data-attributes — no init call, no build step, no dependency. It is a
classic script on purpose: ES modules are blocked on `file://`, and a single
double-clickable .html has to keep working. Nothing here adds style; it only
toggles state `ui.css` already describes, so removing the file leaves the page
readable rather than broken.

| Markup | Behaviour |
|---|---|
| `<button data-ui-open="#id">` + `<dialog class="ui-dialog" id="id">` | Modal via native `showModal()`; `data-ui-close` on any button inside |
| `<button data-ui-menu="#id">` + `<div class="ui-menu" id="id">` | Anchored menu, arrow keys, type-ahead, Esc restores focus |
| `<div data-ui-tabs>` with `.ui-tablist` / `.ui-tab[aria-controls]` | Tabs; ARIA and roving tabindex applied for you |
| `<div class="ui-accordion" data-ui-accordion="single">` | One `<details>` open at a time |
| `<table class="ui-table" data-ui-sort>` | Sortable headers; `data-sort-value` on a cell to sort by something other than its text |
| `<input data-ui-filter="#table" data-ui-filter-status="#count">` | Live row filter with a count |
| `<button data-ui-copy="#el">` / `data-ui-copy-text="…"` | Clipboard, with a `file://` fallback |
| `<form data-ui-validate>` | Native rules, your styling; errors on blur then live. `data-ui-rule` for a custom expression over `value` |
| `data-ui-tip="…"` | Tooltip on hover **and** focus |
| `<div class="ui-scrim" data-ui-palette="mod+k" hidden>` | Command palette; fires a `ui:command` event |
| `data-ui-theme` (select or button), `data-ui-mode="toggle"`, `data-ui-density` (range) | Switch and persist the two axes |

API: `UI.init(container)` after injecting markup (idempotent), `UI.toast(msg,{tone})`,
`UI.confirm({title,body,tone})` → Promise, `UI.open/close`, `UI.setTheme`,
`UI.setDensity`, `UI.toggleMode`.

**Trap:** the HTML `pattern` attribute is compiled with the `v` regex flag, where
`[a-z0-9-]` is a syntax error — and an uncompilable pattern is *ignored*, so the
field silently accepts anything. Escape it: `[a-z0-9\-]`. `ui.js` detects this,
warns, and keeps enforcing the rule under the `u` flag.

## Themes

| Theme | Character | Reach for it when |
|---|---|---|
| `vanilla` | Neutral but designed | Default. Open-source distribution, or the audience is undefined. |
| `blueprint` | Technical console — square, mono, cyan | Developer tools, infrastructure, expert operators. |
| `halo` | Soft depth — translucent, mint, generous | Consumer-facing, modern, unintimidating. Not for dense data. |
| `graphite` | Calm precision — cool near-mono | Internal tools used all day; should recede. |
| `oxide` | Warm industrial — rust, heavy, tight | Trades, hardware, manufacturing, logistics. |
| `vellum` | Editorial calm — bone, serif, airy | Content, research, documentation, reports. |

Every theme defines both modes. `data-mode` is optional — omit it and the theme's
preferred mode applies.

## Archetypes

| File | Structure |
|---|---|
| `app-shell.html` | Fixed rail + main. Toolbar, stat tiles, data table, banner. The dashboard/admin pattern. |
| `portfolio.html` | Banded page, no rail. Hero, full-bleed feature, snap reel, column wall, long-form. Content and gallery sites. |

The two are alternatives, not variants: pick by what the thing IS. A rail answers
"where do the controls live", a band stack answers "where does the content live",
and reaching for the shell by default is what produces six sites that look identical.

**Content-page primitives** (portfolio and anything like it):

| Class | Does |
|---|---|
| `.ui-page` | Band stack. Also clips the scrollbar-width overhang a bleed causes — a bleed must live inside one |
| `.ui-band` | Full-width strip; `-tight`, `-flush`, `-line`, `-sunk` |
| `.ui-measure` | Centred column inside a band; `-text` (68ch), `-wide` |
| `.ui-bleed` | Escapes the measure edge-to-edge without leaving the flow |
| `.ui-cols` | Auto-fit grid — column count follows width, no breakpoints. `--ui-tile` sets the minimum |
| `.ui-wall` | Column flow for unequal heights. Reads DOWN each column, so never where sequence carries meaning |
| `.ui-reel` | Horizontal scroll with snap |
| `.ui-frame` | Aspect-ratio box that reserves space before the image exists; `--ui-ratio` or `.ui-ratio-*` |
| `.ui-figure` / `.ui-caption` / `.ui-frame-label` | Captions beside or over the image |
| `.ui-display` / `.ui-lead` / `.ui-prose` / `.ui-quote` | Hero and long-form type. `--ui-display-mult` scales the hero |

**Lazy images:** put `data-ui-lazy` on the `.ui-frame`. A plain `src` gets native
`loading="lazy"` plus the fade — that is the default and it survives JS being off.
`data-src` defers the request until a screen away, which saves more but needs JS.
Cached images skip the fade deliberately; a flicker on every scroll-back is worse
than no animation.

More archetypes land in `archetypes/`. If the one you need does not exist, build it
from `ui.css` primitives and save it there rather than writing one-off CSS.

## Rules

- **Never hardcode a colour, radius, font or spacing value in an archetype.** If a
  value is needed that no token supplies, add the token to the contract in `ui.css`
  and give every theme a value for it. A hardcoded value is a bug — it silently
  breaks the other five themes.
- **Semantic colour is not the accent.** `--ui-good/warn/crit` stay independent of
  `--ui-accent` so a rebrand cannot break state meaning.
- **State needs a non-colour cue.** Pills carry a dot and a border, not just a hue.
- **Wide content scrolls itself.** Wrap tables in `.ui-scroll`; the page body must
  never scroll sideways.
- **Three text levels only** — `--ui-text`, `--ui-text-dim`, `--ui-text-faint`. A
  fourth is a hierarchy nobody can perceive.
- **Density is one number.** Change `--ui-density` to go compact or comfortable;
  do not touch component padding.

## Authoring a theme

Copy the `vanilla` block in `themes.css` and change values, not structure. Split is:
base block holds shape, type and density; the two mode blocks hold colour only.
Repeat the preferred mode's colours in the base block so `data-theme` works without
`data-mode`.

Before shipping, verify against the checklist in `references/palettes.md`: contrast
ratios, greyscale survival, accent/semantic separation, both modes.

## References

- `references/palettes.md` — choosing and verifying a palette by audience. Read this
  before picking a theme for a real project, and before agreeing to any request
  framed in terms of colour psychology.
