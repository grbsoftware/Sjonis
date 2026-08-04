# Sjonis — handoff

Project name: **Sjonis**. Lives at `C:\Users\grben\Design`.

Written 2026-08-03 at context ceiling. Current state, decisions, and dead ends.

## Who / how to work

Gary: hardware + network background, artist, "vibe coder." Knows how systems talk,
not framework specifics. **Has ADHD — keep replies short.** Lead with the answer,
few bullets, one next step. Detail goes in files, not chat. When he says a tangent
is irrelevant, drop it completely.

He wants push-back, not a menu of options. Act as expert web designer / UI-UX dev.
His friend **Ken** is a real coder and a useful second opinion — take his input
seriously but check it against Gary's actual requirements.

**Never use the Claude-in-Chrome tools** — they corrupted his MSIX install and
forced a Claude Desktop reinstall. Use WebSearch/WebFetch.

## What exists

```
core/ui.css          structure + components, zero colours
core/themes.css      6 themes x light/dark
core/ui.js           LAYER 2 — behaviour. classic script, no deps, no build
demo/behaviour.html  exercises every behaviour, all 6 themes live
tokens/themes.tokens.json   W3C DTCG, generated from CSS
tokens/fonts.json    15 OFL fonts, curated shortlist
tools/css_to_tokens.py, build_themes.py   (Python — NO NODE on this machine)
adapters/tailwind-v4.css, shadcn.css
archetypes/app-shell.html
dist/gtk/, dist/xaml/    generated, 12 files each
demo/gallery.html    live tuner: layout x theme x density/radius/accent + CSS export
.claude/skills/ui-suite/  SKILL.md + references/palettes.md
```

Artifacts: [tuner](https://claude.ai/code/artifact/089593e5-f49b-4b33-ae38-de4964fde67d) ·
[iteration 01 specimens](https://claude.ai/code/artifact/5df3c67f-ff6f-4635-9808-73dbeddc1681)

Always run `python tools/build_themes.py verify` after touching themes
(427 tokens, 18 blocks, currently lossless).

## Architecture (settled)

Two independent axes. **Archetype** = structure, chosen by what it is.
**Theme** = appearance, chosen by who it's for. Archetypes contain no colour,
size or typeface — only `--ui-*` tokens. Vanilla CSS, no build step for consumers.

Themes: vanilla (open-source default), blueprint, halo, graphite, oxide, vellum.
Gary's favourites: **halo** and **blueprint** (opposite poles — that's why the
two-axis split is right).

## Traps already hit — do not re-learn

1. **`var()` in a custom property is substituted where DECLARED.** The `--ui-s*`
   scale had to move from `:root` to `:root,.ui`, or density silently does nothing
   when a theme sits on a descendant. This broke theme density too, not just the
   slider.
2. **shadcn's `--accent` is its hover surface, NOT the brand colour** (`--primary`
   is). Mapping our accent onto it turns every hover neon. Adapter handles it.
3. **Halo is the least portable theme** — depends on `backdrop-filter`, which is
   compositor-dependent on Linux and unreliable in WebKitGTK (what Tauri uses).
   Blueprint is the most portable.
4. **Tailwind `@theme inline`** — the `inline` keyword is load-bearing; without it
   values bake at build time and freeze to whichever theme compiled.
5. **`[hidden]` is a ZERO-specificity UA rule**, so any class that sets `display`
   beats it — `.ui-scrim{display:grid}` left a "hidden" overlay covering the
   page. `ui.css` now restates `.ui [hidden]{display:none}` above class level.
6. **The HTML `pattern` attribute compiles with the `v` regex flag**, where
   `[a-z0-9-]` is an invalid character class — and per spec an uncompilable
   pattern is *ignored entirely*, so the field silently accepts anything. Worst
   possible failure mode. Escape as `[a-z0-9\-]`. ui.js detects, warns, and
   re-enforces under `u`.
7. **Never flag "already wired" in a data-attribute.** `dataset.uiMenu` IS
   `data-ui-menu` — the flag overwrote the selector it was about to read. ui.js
   keeps wiring state in a WeakMap, off the DOM entirely.
8. `<dialog>`'s `close` event and `<details>`'s `toggle` event are **queued, not
   synchronous**. Tests that assert immediately after will see the old state.

## Positions taken

- **Colour psychology is mostly unevidenced.** Meaning is learned and contextual
  (Elliot & Maier, colour-in-context). Blue+orange+grey works for tools via
  *category convention* + *contrast role-separation*, not innate feeling. The
  suite encodes audience presets with stated reasoning. See references/palettes.md.
- **Font "science" is half real.** Legibility (x-height, counters, character
  differentiation) is solid research. Personality ("serif = trustworthy") is
  convention. Dyslexia-specific fonts test poorly.
- **Python for tooling, not C.** C has no JSON and no regex on Windows; needs a
  compiler per platform. Tokens are the asset, the generator is disposable.
- **Don't base the core on shadcn.** It's React+Tailwind+build step and ships one
  look — the opposite of the multi-look requirement. Adapters instead.

## OPEN — the two live threads

### 1. Layout monoculture (Gary's critique, valid)
Everything built so far is ONE paradigm: rail + main, operator-facing, data-dense.
Dashboard / split / settings / palette are four **pages of the same app**, not four
layouts. Gary noted his friend got near-identical output from Fable — mode collapse
toward SaaS admin.

Missing genuinely different skeletons: **artist/portfolio** (full-bleed, masonry,
horizontal scroll), **game** (HUD, hero art, leaderboards, loud display type),
**editorial/zine** (multi-column, pull quotes, overlap), **marketing**, **media
player**, **storefront**.

Honest gap: `ui.css` has **no grid system, no image handling, no hero primitives**.
The "just add markup" claim stops being true here. This needs real new CSS.

### 2. Font DB scale
Gary asked why only 15 fonts, not hundreds. He's right — cataloguing is nearly
free, bundling is what costs bytes. Those are different questions and I conflated
them. Plan: pull the real Google Fonts catalogue (~1,900 OFL families), keep
honest metadata (license, category, variable, weights = real; x-height and
distinctiveness = my judgment, so compute from font files or leave blank at scale).
The valuable part is **filtering**, not the list.

## DONE since last handoff — layer 2

Gary asked "what is the next layer, something js/react related right?" — yes.
CSS = faceplate, JS = wiring, React = control system. **Layer 2 is now built**:
`core/ui.js`, ~36 kB unminified, zero dependencies, no build step.

Deliberate constraints: classic script not an ES module (modules are blocked on
`file://`, and double-clicking one .html must keep working); declarative
data-attributes so no init code can be forgotten; and use the platform —
`<dialog>` for modals, `<details>` for accordions, the constraint-validation API
for forms. Each of those is a focus trap or state machine we would otherwise get
subtly wrong. Everything degrades: remove the file and the page still reads.

Covers dialog + promise-based confirm, anchored menu with type-ahead, tabs,
accordion, toast, tooltip, sortable table, live filter, clipboard, form
validation, command palette, and runtime theme/density/mode with localStorage.
All verified working in-browser across themes; see traps 5–8 above, all four
were found and fixed during that verification.

**Layer 3 (React) is still not started** — and worth questioning before starting.
It buys component reuse and state, but costs the no-build-step property that is
currently the suite's best feature. A thin `useUI()` wrapper over these same
data-attributes may be enough.

## OPEN — still the bigger win

Thread 1, layout monoculture (above), is untouched and remains the highest-value
work. `ui.css` still has no grid system, no image handling, no hero primitives.
Gary said he's "ok with the current layout as a prototype," but four pages of one
SaaS admin app is still one layout.
