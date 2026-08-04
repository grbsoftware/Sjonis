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
core/themes.css      6 themes x light/dark (589 tokens, 18 blocks)
core/ui.js           LAYER 2 — behaviour. classic script, no deps, no build
demo/behaviour.html  exercises every behaviour, all 6 themes live
demo/img/*.svg       14 placeholder drawings, transparent grounds
archetypes/portfolio.html   banded content page — the anti-admin archetype
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
9. **`100vw` includes the vertical scrollbar; the page's width does not.** Every
   `.ui-bleed` overhung by ~15px and gave the document a horizontal scrollbar.
   `.ui-page` now sets `overflow-x:clip` — `clip`, not `hidden`, because hidden
   makes it a scroll container and breaks `position:sticky` inside.
10. **Native controls are painted by the UA, not by CSS.** Dark themes had
   white-on-white `<select>` drop-downs until `--ui-scheme` drove `color-scheme`.
   Same fix covers scrollbars, carets, spinners, date pickers.
11. **A translucent token on a UA-painted surface has nothing behind it.** The
   `<select>` option rule painted with `--ui-surface`; halo is the only theme
   whose surfaces are `rgba`, and in dark that is `rgba(255,255,255,.055)` —
   composited over the UA's own white popup base, not over our page, so it
   resolved to near-white under near-white `--ui-text`. Invisible. Halo *light*
   passed by luck (.72 white over white, dark text), which is why it read as a
   dark-mode-only bug. Rule: UA surfaces get `--ui-bg`, the only ground that is
   opaque in all six themes. Gary found this one.
12. **The preview pane caches `core/*.css` and `ui.js` hard.** Edits appear not
   to work. Test with a cache-busted copy:
   `sed -e "s|../core/ui.css|../core/ui.css?v=$(date +%s)|" … > demo/_x.html`
   (gitignored), and delete it after. It also reports every element as visible,
   so IntersectionObserver work can only be confirmed with a tall spacer probe.

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

## DONE — layout monoculture, first half

**`git` is now in use.** Gary asked for it specifically so the look cannot drift
between versions unintentionally. Commit anything that changes appearance, with
a message saying what moved and why. `python tools/build_themes.py verify` before
every commit.

`archetypes/portfolio.html` shares no layout code with the app shell: no rail, no
toolbar, no table. A stack of full-width **bands**, each with a centred
**measure**. It needed the primitives ui.css genuinely lacked, all now in:

- `.ui-page` / `.ui-band` / `.ui-measure` / `.ui-bleed`
- `.ui-cols` (auto-fit, no breakpoints), `.ui-wall`, `.ui-justified`, `.ui-reel`,
  `.ui-marquee`
- `.ui-frame` aspect-ratio boxes, `.ui-figure`, `.ui-caption`, `.ui-frame-label`
- `.ui-display` / `.ui-lead` / `.ui-prose` / `.ui-quote`, derived `--ui-fs-display`

**Justified rows** are the gallery layout: give each item a `flex-grow` AND
`flex-basis` proportional to its aspect ratio and every item in a row lands on
the same height. `<i class="ui-fill">` (huge grow, zero height) can only reach
the last row, where it stops two leftovers stretching to half the page.

**Lazy loading** — Gary wants this free because galleries charge for it. Native
`loading="lazy"` does the download deferral; the value added is the reserved box,
the shimmer, the fade, the error state, and NOT fading cached images (flicker on
scroll-back is worse than no animation). `data-src` defers harder but needs JS.

**Marquee** — auto-scrolls, track cloned in JS for a seamless loop, clones
`aria-hidden`. Pauses on hover, focus and click (10s), stops when the tab is
hidden, and under `prefers-reduced-motion` it stops moving and becomes a
scrollable reel — hidden overflow plus no animation would strand the content.

**Categorical colour** — `--ui-cat-1..8`, identity rather than state, validated
with the dataviz skill's Python validator against every theme surface. Position
held and agreed: the four state colours keep their conventional hues; themes vary
the hue, never the role. Node is NOT installed — use `validate_palette.py`, and
set `PYTHONIOENCODING=utf-8` or it dies on cp1252.

## NEXT

A second non-admin archetype, to prove the new primitives generalise past one
page — **editorial/zine** or **storefront**. Gary was offered these and picked
portfolio first; the other two are still open. After that: layer 3 (React) is
still unstarted and still worth questioning, because it costs the no-build-step
property that is currently the suite's best feature.

## Working with Gary — what came up this session

- He catches real regressions. He spotted that baking a background into the
  placeholder SVGs broke theming (they're transparent now, so the art takes the
  theme's ground). Take his visual reports seriously and go measure.
- Credit generated art as **generated by Claude, reviewed and approved by Gary**.
  His reasoning: unreviewed AI work presented as finished reflects badly on
  Anthropic. He also asked for the artist link to point at anthropic.com.
- He asks good structural questions (density vs text size) — answer the contract
  question even when deferring the feature.
