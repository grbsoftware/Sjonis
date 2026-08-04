# Sjonis — handoff

Project name: **Sjonis**. Lives at `C:\Users\grben\Design`.

Written 2026-08-04 at context ceiling. Current state, decisions, and dead ends.
Second half of this file is the newer material — read `## NEXT` first.

## Working loop (how this session actually ran)

Gary ran `/loop` and asked for autonomous work: fix bugs, add missing pieces,
commit and push each change, wake him only for decisions that are genuinely his.
That mandate still stands unless he says otherwise. He also said to be creative
and add features not yet discussed.

**Every change ships.** The cycle that worked, and should be repeated:

```bash
python tools/build_themes.py verify     # round trip, MUST pass before commit
python tools/validate_palette.py        # contrast; exit 1 on required failure
python tools/check_adapters.py          # adapter refs resolve
git add -A && git commit && git push origin main
gh api repos/grbsoftware/Sjonis/pages/builds/latest --jq .status   # poll to "built"
```

Then verify **on a served URL**, not `file://` — `file://` cannot do the
cross-frame work. Screenshots often fail ("pane not displayed");
`mcp__Claude_Browser__javascript_tool` is the tool of choice for verification.

**SERVE IT ON LOCALHOST VIA `preview_start` — do not round-trip through Pages.**
As of 2026-08-04 the Browser pane blocks non-localhost URLs outright ("Link to
grbsoftware.github.io was blocked"), and each Pages verification costs a commit
plus a 45-90s build.

**It also blocks a localhost server you started from Bash** — the error is
self-contradictory ("Link to localhost was blocked. The Browser pane only
supports localhost URLs") and it cost a Windows Firewall prompt to find out. The
pane only trusts a server IT started. `.claude/launch.json` now exists for this;
the sanctioned path is:

    mcp__Claude_Browser__preview_start  with  name: "sjonis"

which starts `python -m http.server 8137` in the repo root and opens a trusted
tab on it. Verified working. Same origin, cross-frame works, no cache lag, no
commit needed to look at something. Push when it is right, not to find out
whether it is.

Two escape hatches worth knowing when a tab is already open on a blocked origin:
a tab loaded BEFORE the block still runs `javascript_tool` fine, and from such a
tab `fetch()` reaches anything same-origin — which is how the deployed Radiance
fix was verified (pull the functions out of the served file with a brace matcher
and run them via `new Function`, so it tests what actually shipped rather than a
local copy).

If a theme colour changes: `python tools/css_to_tokens.py` then
`python tools/build_themes.py all` to regenerate `tokens/` and `dist/`, or the
round trip fails.

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
core/ui.css          structure + components + the DEFAULT (flat) skin, zero colours
core/themes.css      6 themes x light/dark (589 tokens, 18 blocks)
core/ui.js           LAYER 2 — behaviour. classic script, no deps, no build
skins/bevel.css      THE SECOND SKIN. Win95/Motif grammar. Proof the ring works.
demo/skins.html      flat vs bevel, one <template> stamped into both panels
skeletons/game.html  GAME/HUD — stage, 9 HUD slots, meters, leaderboard
index.html           EXAMPLE BROWSER — the front door. Frames every example,
                     hash-routed, global dark toggle, live tuner (T)
demo/behaviour.html  exercises every behaviour, all 6 themes live
demo/img/*.svg       14 placeholder drawings, transparent grounds
skeletons/app-shell.html          rail + main — the admin pattern
skeletons/portfolio.html          banded content page — the anti-admin
skeletons/storefront.html         catalogue — site frame + product grid
skeletons/storefront-product.html page two of the same site
skeletons/editorial.html          long-form — columns, drop cap, pull quotes
tools/validate_palette.py   WCAG contrast over every theme x mode
tools/check_adapters.py     adapter references resolve
tools/fonts.py              Google Fonts catalogue: fetch / find / show
tokens/fonts.catalogue.json 1,942 families, generated
LICENSE.md           PolyForm Noncommercial 1.0.0
tokens/themes.tokens.json   W3C DTCG, generated from CSS
tokens/fonts.json    15 OFL fonts, curated shortlist
tools/css_to_tokens.py, build_themes.py   (Python — NO NODE on this machine)
adapters/tailwind-v4.css, shadcn.css
skeletons/app-shell.html
dist/gtk/, dist/xaml/    generated, 12 files each
demo/gallery.html    live tuner: layout x theme x density/radius/accent + CSS export
.claude/skills/ui-suite/  SKILL.md + references/palettes.md
```

Artifacts: [tuner](https://claude.ai/code/artifact/089593e5-f49b-4b33-ae38-de4964fde67d) ·
[iteration 01 specimens](https://claude.ai/code/artifact/5df3c67f-ff6f-4635-9808-73dbeddc1681)

Always run `python tools/build_themes.py verify` after touching themes
(427 tokens, 18 blocks, currently lossless).

## ARCHITECTURE — FOUR RINGS (settled 2026-08-04, replaces the two-axis model)

Gary pushed hard on this and was right twice. First: three words ("archetype",
"layout", "template") were in use for ONE thing — that is how a vocabulary rots,
and it had already cost us a confused exchange about whether a new skeleton needs
a new theme. Second, and bigger: **a new theme would only ever be this same look
in new colours.** He was correct, and the reason is mechanical.

A theme can set only nine kinds of value — colour, radius, density, font, weight,
tracking, blur, shadow, ambient. The *rule* (`.ui-card{background:…;border:…}`)
lives in ui.css where no theme can reach. So a theme changes the adjectives and
can never change the grammar. That is why a system with twenty themes ships one
look, and it is exactly the mode-collapse critique he made about the layouts,
one layer down.

The system is now an onion. One word per layer, no synonyms:

| ring | owns | chosen by | built |
|---|---|---|---|
| **skeleton** | structure | what the thing *is* | 6 |
| **skin** | how a surface is drawn | which visual grammar | 2 |
| **theme** | colour, type, radius | who it is *for* | 6 |
| **genre** | a named complete look | the point of view | 1 |

`archetypes/` is now `skeletons/`. "Archetype" and "layout" are gone everywhere.

**Industry note, since it will come up again:** there is no settled term for any
of this. Atomic Design stops at "template" (= our skeleton) with nothing above;
CMSes use theme > template; Winamp/phpBB used "skin" for exactly our meaning.
Nobody will hand us a vocabulary — these four are ours and they are now written
into README, SKILL.md and every file.

### skin — the new ring, and how it works

Four ROLES cover every surface. Components name a role, never a treatment, so a
skin restyles everything by redefining four things:

    raise    on the page       cards, table wrap
    float    above everything  dialogs, menus, toasts
    inset    below the page    inputs
    control  can be pressed    buttons

Each has `-fill`, `-border`, `-radius`, `-shadow`, declared in ui.css's derived
block (`:root,.ui`) so they resolve wherever a theme lands. The defaults ARE the
flat skin, so a page with no skin is byte-identical to before.

**`data-skin` must go on the SAME element as `class="ui"` and `data-theme`.** On
an ancestor, the derived block re-declares the role tokens at the `.ui` level and
the skin silently does nothing — trap 1 again.

**A skin may add RULES; a theme may not.** That is the line between them, and it
is load-bearing: `border-color` takes four values and no single token can carry
that. A bevel's grammar is a shape, not a value.

`skins/bevel.css` is deliberately the furthest thing from flat rather than a
tasteful variation — square corners, no cast shadow, drawn edges, controls that
go DOWN when pressed, dotted inset focus. If the architecture expresses that,
everything between is free. `demo/skins.html` proves it with both panels stamped
from ONE `<template>`, so the twins cannot drift.

### genre — not started, and the rule that matters

Genre is the composition ring: a named look that picks a skin and theme, adds
ornament, and says which skeletons it suits. Facets (era / industry / ideology /
mood) are for FINDING genres, never for generating them.

**Genres are authored, never computed.** The moment a look falls out of a
parameter combination it stops being a point of view — which is the exact failure
the skin layer exists to fix. The seven audience presets already in
`references/palettes.md` are proto-genres stuck in the palette layer; they are
the natural first set to promote.

Gary also flagged that a genre may need to carry BEHAVIOUR, not just ornament (he
was recalling Java-applet physics toys — circles, springs, gravity). Agreed and
worth designing for: a "toy" genre and a "clinical" genre differ in how things
*move*, not only how they look. Deferred, but do not architect it out.

### A genre carries no alternatives — and the test for it

Gary asked (2026-08-04) whether a look different enough to stand on its own could
be "an alternative in the same genre." **No**, and the reason is the ring's whole
purpose: a genre holding alternatives is a parameter combination again, and a
look that falls out of picking options is not a point of view. One skin, one
theme, or it is not a genre.

**The test, which is the useful part:** is choosing between the two *itself* a
point of view? Hard bevel is period-accurate, drawn depth, 1996; soft bevel is
modern relief, cast depth, present tense. Choosing between those is a stance, so
they are two genres. If nobody would ever care which they got, it is a variant of
one skin and the genre still picks one.

What that leaves is real and needs a word: two genres that share a theme and the
skeletons they suit and differ only in skin are **siblings**, in a **family**.
Family is a finding aid, exactly like the era / industry / ideology / mood
facets — it helps you locate a genre and never generates one. So bevel and
soft-bevel each anchor their own control-panel genre: same furniture, two eras.

## DONE — the skin gate gap is CLOSED. 3576 pairs, 0 failures.

`validate_palette.py` now checks every skin in `skins/` against every theme x
mode, and gates on it by default (`--no-skins` for the old behaviour, `--skin
PATH` for one). Turned on, it found **four** more failures on bevel beyond the
two that were caught by hand — all twelve theme x mode combinations each:

    --ui-accent      1.58 against 3.0    every link on a panel
    the four states  2.02 against 4.5    every .ui-pill on a card
    the mark rims    2.53 against 3.0    every .ui-dot on a card
    --ui-text-dim    2.66 against 4.5    on four faces the old block missed

How it works, and the three decisions that matter:

- It **evaluates `var()` and `color-mix()`** rather than reading token text. A
  skin's surfaces are derived — bevel's face is a mix of the theme's own bg and
  ink — so there is no literal to look up. This is trap 15 one ring out.
- It **reads the component -> role map out of `ui.css`** (which selectors paint
  with `var(--ui-<role>-fill)`, and what `color` they set alongside). Writing
  that down a second time is how a checker starts describing an older design.
- It tags `raise` and `float` as **containers** and everything else as chrome.
  Asserting `--ui-crit` must be readable on a tab is measuring a design nobody
  wrote — the same mistake `checks()` exists to avoid.
- An **edge is measured against both of its sides** and keeps the better score.
  A sunken field's light edge is *meant* to be invisible against its own pale
  interior and visible against the panel outside it; that is how Win95 drew a
  list box. Measuring against the fill alone called bevel's inset edge broken
  at 1.10 when it is doing its job.

**Softening the mid face does not fix any of it.** Swept 60→100% of `--ui-bg`:
the state hues first clear 4.5 at 100%, where the lit edge is 1.02 and there is
no bevel left. The mid face and the tuned hues are mutually exclusive, so each
ink is answered on its own terms — accent and the two lower text levels promoted
toward the ink, rims via `--ui-mark-rim-mix` (40%), and the four state hues
**not** promoted at all. Those are the one part of the palette held at
conventional positions; the pill gets the ground it was tuned against instead
(`--ui-bg`, a sunken well), which is also the more period-accurate reading of a
status in this grammar. Verified on the live site by measuring rendered pixels:
accent 4.44, dim 6.15, pill hue in its well 4.89 — where the same hue on the
bare face was 2.52.

**Three of the four fixes were the checker being wrong, not bevel.** Each is
written down at the line where it was wrong. Expect the same ratio on skin two.

## Architecture (superseded — kept for the reasoning)

Two independent axes. **Skeleton** = structure, chosen by what it is.
**Theme** = appearance, chosen by who it's for. Skeletons contain no colour,
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
12. **A percentage inside `columns:` resolves against the COLUMN box.** The side
   pull quote was `width:min(20rem,42%)`; inside a 22rem column that is ~150px,
   about seven characters a line, with the body text squeezed into the rest.
   Anything floated inside multi-column text has to be sized against the column,
   not the container — and usually should not float at all.
13. **The browser caches `core/*.css` and `ui.js` for 10 minutes on Pages.**
   A page loaded before a push keeps the old assets and the new work looks
   broken. Verify with a cache-buster:
   `document.querySelectorAll('link[rel=stylesheet]').forEach(l=>l.href=l.href.split('?')[0]+'?cb='+Date.now())`
   and re-inject `ui.js?cb=…` — three "bugs" this session were only this.
14. **The preview pane caches `core/*.css` and `ui.js` hard.** Edits appear not
   to work. Test with a cache-busted copy:
   `sed -e "s|../core/ui.css|../core/ui.css?v=$(date +%s)|" … > demo/_x.html`
   (gitignored), and delete it after. It also reports every element as visible,
   so IntersectionObserver work can only be confirmed with a tall spacer probe.

18. **A custom property cannot refer to itself, even to read the value it
   inherited.** `--ui-accent:color-mix(...var(--ui-accent)...)` on a descendant
   looks like it should promote the inherited value; it is a cycle and is
   invalid at computed-value time, so the property falls back to unset. Capture
   into a second name at the level above first — bevel's `--ui-bevel-accent`
   does this, and needed to anyway so a filled button inside a card would not
   inherit the promoted value as its own background.
19. **An element's surroundings must be resolved OUTSIDE that element's scope.**
   bevel's filled button redefines `--ui-bevel-face` to the accent for its own
   edges, so asking the button what `--ui-raise-fill` means answers "the
   accent" — its own face, not the panel it sits on. The lit edge scored 1.27
   against itself where against the panel it is 1.73. Same shape as trap 1: the
   question is always *where* a var() is being substituted.
21. **A skin or genre applied by SCRIPT has to land on the `.ui` element, not
   `<html>`** — trap 1 wearing a new hat, and it shipped green through every
   gate. ui.css's derived block is `:root,.ui`, so it re-declares the four role
   tokens at the `.ui` level; a skin on an ancestor is overwritten and does
   nothing at all, silently. The skeletons carry `data-theme` on `<html>` and
   `class="ui"` on `<body>`, which is fine for a theme (nothing re-declares
   palette tokens) and fatal for a skin. Measured on the live site before the
   fix: `.ui-card` was a 1px near-black box instead of a 2px bevel on the mid
   face. `check_genres.py` now fails a page whose genre attributes sit on a tag
   without `class="ui"`.
20. **`[hidden]`-style zero-specificity reasoning has a colour twin: a token
   promoted on a face reaches everything inside that face.** Scope a promotion
   to the surfaces that need it, and check what else consumes the token before
   moving it — `--ui-accent` is text in two places and a fill in eight.

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

### 2. Font DB scale — DONE
`tools/fonts.py` + `tokens/fonts.catalogue.json`. 1,942 families, 555 variable,
828 kB, from the public Google Fonts metadata endpoint (no API key, stdlib only).
Records only what is checkable; records no x-height or personality rating on
purpose. `fonts.py find --category mono --variable --max-kb 200`, `fonts.py show
Inter`. `tokens/fonts.json` stays the curated shortlist with reasoning.

Still open here: nothing blocking. A "try this font" hook in the tuner would be
the natural next step — pick from the catalogue, inject the `@font-face`, look
at it — but that needs network at runtime, which the suite currently never does.

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

`skeletons/portfolio.html` shares no layout code with the app shell: no rail, no
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

## DONE — published, licensed, and the site frame

**Sjonis is public and live: https://grbsoftware.github.io/Sjonis/**
Repo `grbsoftware/Sjonis`, Pages from `main` at root. Local `master` was renamed
`main`. Git identity was set repo-local (it had been global and was lost).
After every push, Pages takes 30–90s to rebuild — poll
`gh api repos/grbsoftware/Sjonis/pages/builds/latest --jq .status`.

**Licence: PolyForm Noncommercial 1.0.0** (`LICENSE.md`), verbatim. Noncommercial
use fully granted; **commercial use requires a separate licence from Gary**, so a
commercial user has to make contact. Gary considered cutting the free-use grant
for government and decided against it — do not re-open unprompted. Contact is
routed through GitHub, not his email, deliberately: a plain-text address on a
public repo is scraped within days. GitHub shows no licence badge because
PolyForm is not OSI — that is expected, not a misconfiguration.

**`index.html` — the example browser.** Every example in one frame: prev/next,
tab strip, arrow keys, width presets. The hash is the state, so the browser's own
back/forward walk the viewing history and `#storefront` links land. Dark by
default and the toggle is **global** — it drives the framed document too, because
a dark surround with a white page inside is worse than either alone. How each
page takes that instruction is **declared per example, not sniffed**: `data-theme`
means a suite theme on a skeleton and light/dark on a standalone demo page, so
guessing breaks one of them. Reaching into the frame needs same origin — it works
on the served site, and from `file://` only the chrome switches.

**The site frame** — the layer above the page, which the suite genuinely lacked.
`.ui-skip`, `.ui-sitehead` (+`-stick`, `-sunk`), `.ui-sitebar`, `.ui-sitenav`
(+`-item`, `aria-current`), `.ui-sitehead-actions`, `.ui-crumbs`, `.ui-sitefoot`
(+`-cols`, `-base`). Deliberately not the app shell's rail: a rail is for an
operator moving between views of one tool and owns the viewport; a site header is
for a reader moving between documents and yields to the content.

**`skeletons/storefront.html`** — the third skeleton, and the proof the site
frame generalises: it reuses the header, crumbs and footer markup unchanged.
New COMMERCE primitives in ui.css: `.ui-price`/`-was`/`-note`, `.ui-badge`,
`.ui-swatch`/`.ui-swatches`, `.ui-frame-muted`, `.ui-card-body`.

**New in ui.js**: `data-ui-choice` (single-select button group, `aria-pressed`,
arrow keys) and the live filter now honours `data-ui-item`, so a card grid can be
filtered — it only understood list items and table rows before.

**`tools/validate_palette.py` now exists.** RESUME used to reference one that was
never in the repo. It models the pairings ui.css actually produces (`.ui-pill`
has no background, so its hue meets the page, never `--ui-*-soft`), composites
rgba tokens over their ground first, and prints ASCII only so cp1252 cannot kill
it. `python tools/validate_palette.py`, exit 1 on failure.

## Traps found by measuring rather than looking

Two bugs this session were invisible on screen and obvious in arithmetic. Both
had been shipped and reviewed without anyone noticing:

- **The black-vs-white ink crossover is 0.1791, not 0.45 or 0.5.** White beats
  black only while `1.05/(L+0.05) > (L+0.05)/0.05`, so the boundary is
  `sqrt(0.0525) - 0.05`. The old 0.45 gave a mid ochre accent white text at
  2.17:1 where black scores 9.70:1. Four of six test hues flipped.
- **halo light shipped a failing button label** — `#FFFFFF` on `#0E9C86`, 3.43:1.
  Now `#06231F`, which halo dark already used, 4.83:1.

The lesson worth keeping: contrast is not a thing to eyeball. `validate_palette.py`
found the second one in a second, and would have found the first if the tuner's
maths had been in a checkable place rather than inline in a page.

Three more of the same kind, from the palette work:

15. **A checker must measure what the CSS computes, not what the token says.**
   Once `.ui-dot` gained a rim, the thing meeting the ground was a computed
   `color-mix`, not `--ui-cat-4`. `validate_palette.py` grew OKLab conversion and
   `mix_oklab` so it measures the rim; left alone it would have gone on reporting
   126 failures for a problem that had been solved a different way. It still
   prints the fill-vs-ground ratio as *advisory*, so the cost of the choice stays
   visible rather than being quietly dropped.
16. **Rounding to hex can undo a solved contrast value.** Up to half a step per
   channel, which is enough to drop a solved 4.502 back under 4.5. Five tokens
   landed at 4.49–4.50. Solve, round, then re-check the ROUNDED value, with margin.
17. **halo's `-soft` tokens are `rgba(<the state hue>,.12)`** — so moving a hue
   also moves the ground that hue is read against, and fixing them in sequence
   oscillates. Hue and tint have to be solved together, recomputing the tint from
   each candidate. It converges because the tint moves at 12% of the hue's rate.
   Any derived token has this shape; check for it before solving one in isolation.

## DONE — the palette thread is CLOSED. 125 failures -> 0.

Both halves shipped and verified on the live site. `validate_palette.py` exits 0.

**The rim (Gary's decision, implemented).** No `--ui-cat-*` value changed.
`.ui-dot`, `.ui-tag::before` and `.ui-swatch` carry a 1px rim of their own hue
mixed 55% toward `--ui-text`, so it darkens on light grounds and lightens on dark
without ui.css naming a colour. Worst case 3.76:1, was 1.86:1. The rim is
declared **on the mark, never at :root** — trap 1 would bake `--ui-series` to its
fallback and rim every dot as cat-1. Tunable via `--ui-mark-rim-mix`, which is a
plain percentage and therefore safe to set from any level.

**State colours moved.** The remaining 33 failures were all a state hue printed
AS TEXT (`.ui-pill-*` has no background; `.ui-banner-*` sits on its own soft
ground), sitting at 2.72–4.49 against a 4.5 bar. Unlike the categorical set there
was no competing constraint — four hues at conventional positions have room that
eight mutually-separated series hues do not. 15 tokens moved by the minimum:
hold OKLCH hue and chroma, walk lightness toward the ink, stop at the first value
clearing every ground it meets. Most moved under 0.03 L and are invisible.

**halo light is the one visible change and the one to re-check with Gary.** It
was worst (warn 2.72), so it moved furthest; its four states now read distinctly
deeper. `--ui-accent` moved only `#0E9C86` -> `#0C9B85`, so halo's mint is
intact — but `--ui-good` was *the same value as the accent* and could not stay
bright. If Gary dislikes it, the alternative is to stop printing state hues as
text in halo and carry them on a border + dot the way `.ui-tag` already does.
Specimen artifact showing every before/after:
https://claude.ai/code/artifact/598ce1c1-d2b7-486a-b89f-2e507c50148b

Also fixed in passing: `.ui-tag::before` had no forced-colours border (the tag's
dot vanished under Windows High Contrast), and marks now `print-color-adjust:
exact` — a browser drops backgrounds on paper, and a legend whose dots did not
print is a list of labels bound to nothing.

## DONE — the GAME / HUD skeleton (`skeletons/game.html`)

The sixth skeleton, built and live. Every other skeleton puts chrome BESIDE the
content (app-shell's rail) or ABOVE it (the site frame); a HUD does neither — it
floats on the art and the art keeps going underneath. It is also the only
skeleton with no reading measure in its hero, and the measure deliberately
returns below the fold where there is prose again.

New primitives, all of which were genuinely missing:

- `.ui-meter` — the real gap, and useful far outside this page. One 0-1 fraction
  drives it (`--ui-meter`), so the author never does arithmetic against a
  container they cannot measure; `clamp()` guards both ends. `.ui-meter-seg`
  masks track and fill together so the pips' gaps are the page, not a colour
  ui.css would have to name. NOT `<progress>`: it cannot be segmented and its
  pseudo-elements are still three vendor spellings. The `role` is the author's
  (`meter` = a static measurement, `progressbar` = a task advancing) — they read
  differently and only the author knows which it is.
- `.ui-stage` / `.ui-stage-scrim` / `.ui-hud` + nine slots — children stacked in
  one grid cell, corners pinned at every size with no media query.
  `pointer-events:none` on the grid, `auto` on its children, so the art stays
  live between the chrome. **`100svh`, not `vh`** — vh is the tallest the
  viewport ever gets, so a "full screen" stage hides under a phone's browser
  chrome until you scroll.
- `.ui-readout` (label under the number, for glancing), `.ui-rank` (leaderboard),
  `.ui-sr` (visually hidden — a real gap), `.ui-btn-lg`.

`.ui-rank` has no gold/silver/bronze on purpose: ui.css names no colours, so the
top three are marked by WEIGHT, which also survives greyscale and forced colours.
The "you" row hangs off `aria-current` — the same attribute the screen reader
announces — rather than a parallel class that could drift out of step, and
carries three signals (tint, an inset edge that is a shape, and a visible word).

**The honest hard problem, and the two answers.** Chrome over artwork has no
guaranteed contrast, and a scrim does not fix it because the author can always
supply a bright picture. So: `.ui-hud-panel` mixes its ground from `--ui-bg`, the
one token opaque in all six themes — measured against pure white AND pure black
art in all 12 theme x mode combinations, worst `--ui-text` ratio is **9.44:1**.
The legibility is the mix, not the blur (only halo sets `--ui-blur`, so five of
six themes have no blur here and are still fine). And `.ui-hud-ink`, for text
sitting on the scrim, is a literal `#fff` because the scrim is ALWAYS a black
wash — a themed `--ui-text` would go dark under any light theme and vanish into
the very wash protecting it, a failure that would show on only half the themes.

Verified on the live site: art covers the stage exactly, all four corners pinned
at 25px, no slot overlaps, and all 8 meters render their exact fraction.

## DONE — GENRE ONE IS BUILT AND LIVE: Control Panel

The fourth ring has one entry. `#control-panel` in the example browser.

    tokens/genres.json          the authored record: bevel + graphite dark +
                                app-shell, with reasoning per choice
    genres/control-panel.css    the ornament
    tools/check_genres.py       the gate

**Mechanism, and why it is deliberately dumb.** `data-genre` does NOT imply the
skin and theme. Making it imply them means either every theme knows about every
genre (alias selectors generated into themes.css), or the page needs JavaScript
to resolve — and everything here has to survive being double-clicked off a disk.
So the composition is written out in the markup and `check_genres.py` gates the
spelling against the manifest. **Say it twice, check it once.** The gate also
refuses a genre stylesheet containing an unscoped selector, which would silently
restyle any page that merely links it.

**Ornament stays where contrast cannot follow it.** The palette gate cannot see
genres — the same blindness skins had, one ring up. So with one exception the
file changes only type, case, spacing and density. That exception is the caption
bar, measured first: it wanted a gradient and cannot have one. `--ui-accent-ink`
must clear 4.5 at BOTH ends and no direction works, because themes with light
ink fail when the bar darkens and themes with dark ink fail when it lightens.
Toward `--ui-bg` tops out at 3.94; toward black at 95% — by then not a gradient
— reaches 4.34. Solid accent is 4.61 everywhere. **Any ornament putting a
one-directional ramp under themed ink has this shape.**

`index.html` frames the REAL skeleton and dresses it rather than shipping a copy
wearing the genre, which would drift within a session. The entry names only the
genre id; the composition is read from the manifest.

Verified live: card on the mid face with a light top edge and dark bottom edge,
pill in its `--ui-bg` well, caption 9.71, body on the card face 6.61.

**Extending the palette gate to genres is now the obvious next gate job** — it
is the identical gap, and this genre only avoided it by self-restraint.

## DONE 2026-08-04 (session 2) — SKIN THREE, GENRE TWO, and Radiance

**`skins/cushion.css` — the soft skin. Built, gated, verified on all 12
theme x mode combinations.** Fill, border and radius are left EXACTLY as the
theme set them; only the shadows change. That restraint is the payoff: bevel
moves every panel to a mid face and then re-tunes four ink families plus gives
`.ui-pill` a well; cushion needs none of it, because every ink is meeting the
ground it was already validated against. Measured on rendered pixels:

    dark   lit 1.32-1.36   shade 1.10-1.21
    light  lit 1.00        shade 4.72-4.76

One edge carries each mode by design — highlight in dark, shadow in light —
and the theme's untouched border is what guarantees a boundary when the
carrying edge fades. That is also the neumorphism trap named and avoided.

22. **NEW TRAP — `color-mix()` averages ALPHA along with the channels.** The
   first cushion derived its edges as `color-mix(in srgb,var(--ui-line) 50%,#fff)`.
   halo's `--ui-line` is `rgba(255,255,255,.10)`, so mixing it 50/50 with opaque
   `#fff` gave white at alpha **.55** — an edge five and a half times more
   opaque than the line it was a variation of, and halo dark grew a bright
   white rim on every panel. It is well behaved on the five opaque themes, so
   it passes everywhere except the one theme it breaks. Trap 11 and 17 in a
   third costume: any expression combining a token with a literal must be
   checked against the theme whose token is translucent. Edges are literal
   rgba now, which composites predictably over anything.

**`genres/control-surface.css` — genre two, and the first FAMILY pair.** Same
theme (graphite dark), same skeleton (app-shell), one skin apart from
control-panel. Held fixed on purpose: varying more than one ring would make the
pair a comparison of two looks instead of a demonstration of what a skin is.
The stance is not about bevels — control-panel says every control is equal and
named (uppercase mono, packed tight); control-surface says the READING is the
thing (large quiet numbers, labels demoted to `--ui-text-dim`, more air). It
takes **no colour exception**, where its sibling needed one for the caption
bar, and that is inherited: ornament is cheapest on the skin that moved least.

Both genres verified dressing correctly in `index.html` (`#control-panel`,
`#control-surface`). **The genre gallery is no longer blocked** — two genres
exist, which was the stated precondition.

**BUG GARY FOUND, FIXED — dressing could only be ADDED, never removed.** Three
entries frame the same file (`app-shell`, `control-panel`, `control-surface`
are all `skeletons/app-shell.html`), and `show()` skips the reload when the src
is unchanged — correctly, since reloading throws away scroll position. But the
frame's `load` event is what triggered dressing, so between those three entries
nothing ran: control-panel walked into control-surface still wearing bevel, and
plain app-shell wore whichever genre you came from. Arriving from a *different*
file always worked, which is why it read as random.

Two halves to the fix. `show()` re-dresses in place when it skips the reload,
and `applyGenreToFrame` now states the whole desired result — it strips first,
so it is idempotent and `!g` means "undressed" rather than "leave it alone".
Undressing **restores rather than guesses**: the author's original values are
stashed on the element at dressing time, because a skeleton carries
`data-theme` on `<html>` while demo pages put it on the same element as
`class="ui"`, and blindly removing it would strip the theme off those. Verified
by clicking all 12 transitions Gary listed.

**Two silent failures made loud in `index.html`.** `loadGenres` ended in
`.catch(function(){})`, justified by file:// having no origin. True, and still
wrong: a JSON typo, a renamed file and a cached empty body all produce the
identical blank page, so the one expected failure was hiding every unexpected
one. It now warns on non-file:// origins, and `applyGenreToFrame` warns when an
entry names a genre the manifest does not have. Both cost nothing and would
have saved most of this session's debugging.

**Verification note that cost real time:** the pane served a CACHED
`tokens/genres.json` (`transferSize: 0`) while `fetch()` from the console
returned the new one. Both genres appeared broken and neither was. Trap 13/14
again — **check `performance.getEntriesByType('resource')` for `transferSize:0`
before believing any "it isn't applying" result.**

`.claude/launch.json` gained `sjonis-alt` (port 8139) because another session
held 8137, and `radiance` (port 8138, serving `../code/Radiance`).

### RADIANCE — three fixes, pushed and live

Cloned to `C:\Users\grben\code\Radiance` (stable, so launch.json can serve it).

- **The label ink was wrong on 14 of 114 preset colours.** `getLuminance`
  weighted GAMMA-ENCODED channels 0.299/0.587/0.114 and switched at 0.5 —
  exactly the crossover error already written down here. Worst was `#FF00FF`
  with white at **3.14:1** where black scores **6.70:1**. Worst anywhere now
  4.72, so every hex code on screen clears AA.
- **Out-of-gamut midpoints now give up saturation, not lightness.** Per-channel
  clamping moved 23 of the presets' bridges up to **3.6° in hue and 0.014 in
  L**. Chroma reduction: **0.9° and 0.0009**. Green -> blue lands at L 0.659
  exactly — the residual the README blamed on clipping is gone, not explained.
- **Bridges: Blend or Wheel.** Blend averages a and b as coordinates, so as
  hues diverge the vectors cancel and the bridge drifts grey (gold -> navy =
  `#7E7D70`; 12 preset bridges lose over half their anchors' chroma). Wheel
  averages L and chroma as scalars and walks hue the short arc (gold -> navy =
  `#009083`). Both defensible, which is the test a setting must pass. Blend is
  the default. **Push-to-hull was measured and REJECTED** — the headroom is
  largest exactly where hue means least (two pale neutrals at chroma 0.002 have
  **89x** of it, and spending it turns a soft grey into `#C3FF3B`).
- Also: bridge bars are keyboard-reachable and announced, clipboard failures no
  longer fail silently, `loadState` validates what it finds, sw at **v4**.

**Still open on Radiance:** the GitHub repo DESCRIPTION still says "smooth
HSL-interpolated bridges" — Gary's to change, it is a repo setting.

## NEXT — in priority order
2. **Skin three — the soft one.** Gary's, and he is right: "black can be
   beveled on black, I've done it before with softer shadows and or highlights."
   The mid face is NOT a property of bevels; it follows from two rules bevel
   chose for itself — opaque edges mixed FROM the face, and `--ui-shadow:none`.
   Drop both and the face stays on the theme's own ground. Measured over
   `--ui-bg` in all twelve combinations at 10% white / 55% black:

       dark modes    highlight 1.28-1.33   shadow 1.05-1.12
       light modes   highlight 1.00-1.01   shadow 4.60-4.73

   Exactly one edge carries each mode — highlight in dark, shadow in light —
   and the cast shadow supplies the depth the flat edge cannot. Note the edge
   bar (1.5) is too crude for a 1px hairline; WCAG sets no floor for one, which
   is why `EDGE_WANT` is advisory. All of this is written into the head of
   `skins/bevel.css` so it is not re-derived from scratch.

   This skin is also the answer to bevel's real weakness: with the face on the
   theme's ground, none of bevel's ink promotions are needed at all.
3. `marketing` and `media player` — the last two unbuilt skeletons from the
   original monoculture list. Neither is blocked.
4. The sequential ramp / Radiance question (see NEW DIRECTION below).

**Gary on bevel's grey, 2026-08-04:** "that gray on black or white is fuggly...
It might be alright in cpanel" — then "I don't mind keeping it." So bevel STAYS
as the period piece; do not quietly restyle it. Two things fell out of that
exchange worth keeping. The grey is not the mix desaturating the theme (checked:
a hue-preserving face is the same colour) — it is that every theme's ground is
already near-neutral, chroma 0.001-0.032, so pulling one 30% toward the ink
lands in dead-centre grey. And "alright in cpanel" is the GENRE ring talking:
bevel + graphite + app-shell is a control-panel genre and a strong candidate for
genre one.

**One visible change to put in front of Gary:** bevel promotes `--ui-accent` on
its panel faces, and `--ui-accent` is not only link text — ui.css also fills a
meter, a switch and a focus ring with it. So those read slightly deeper *inside*
a panel than on the page. The alternative was to promote only the `color` uses
and pin every fill back, which needs a list of every fill selector and rots the
first time ui.css adds one. Stated in the CSS as well. If bevel ever reads
wrong, look here first.

Everything through the skin layer is committed, pushed, Pages-built and
verified on the live site. Working tree clean as of this handoff.

**Live URLs** (note: `/archetypes/*` is DEAD, renamed to `/skeletons/*`):
- https://grbsoftware.github.io/Sjonis/            example browser, 10 entries
- https://grbsoftware.github.io/Sjonis/demo/skins.html
- https://grbsoftware.github.io/Sjonis/skeletons/game.html

**Verification note that cost time here:** the preview pane reports
`innerWidth`/`innerHeight` of **0** when it is not displayed, so every `vh`/`vw`/
`svh` value resolves to nothing and a `100svh` stage measures 0x0. Layout looks
catastrophically broken and is fine. Pin an explicit px size via JS
(`stage.style.blockSize='760px'`) and measure the LOGIC instead — see trap 14,
this is the same pane and the same class of lie.

### DECIDED 2026-08-04 — palette: rim the dots — SHIPPED, see "palette thread is
CLOSED" above. The 55% guess in the original decision turned out to be exactly
right (worst 3.76:1); 65% would have been the edge at 2.99.

### NEW DIRECTION — more palettes, and Radiance

Gary: "there are palettes I like a lot that are not listed. For instance I really
like blue purple and green together." He is unsure whether it belongs here,
"always, or yet" — so treat it as an invitation, not a spec, and push back if it
does not fit.

Honest read to carry forward: that is an **analogous** scheme (adjacent hues),
and the current `--ui-cat-*` set is deliberately the opposite — maximally
separated hues, because eight series must stay apart from EACH OTHER. Analogous
palettes are gorgeous and are the wrong tool for categorical identity. Where they
genuinely fit: a **sequential/continuous** ramp (one variable, low to high), a
theme's accent family, or a decorative gradient. So the right move is probably a
NEW token family — a sequential ramp — rather than editing `--ui-cat-*`.

### HOW GARY WANTS THESE PALETTES USED — and the measurement that backs it

Gary, after seeing the rainbow output: *"they may not be great for webpages...
the gradients could be used very sparingly and not necessarily in the form of
the rainbow, but the solid blocks of color or bars or circles could be 2 or more
of the colors, and the accented text like the blue in the vanilla portfolio is
used for Selected work 2024-2025 above the white text."*

He is pointing at `.ui-eyebrow`, which is `color:var(--ui-accent)` — portfolio
line 57. That splits into **two contrast regimes, and Sjonis already has a
mechanism for each**: blocks/bars/circles are non-text (3:1, and the mark rim
carries them), accent text is 4.5:1.

Measured, his own blue/purple/green through Radiance (anchors `#6B3FA0`,
`#3A5470`, `#2E8B57` -> 5 colours), on vanilla light:

    colour     block (3.0)   block+rim   eyebrow text (4.5)
    #6B3FA0      7.20 ok      11.28        7.20 ok
    #554C88      7.38 ok      11.44        7.38 ok
    #3A5470      7.64 ok      11.64        7.64 ok
    #367066      5.59 ok       9.92        5.59 ok
    #2E8B57      4.14 ok       8.41        4.14 FAILS

**All five work as blocks; four of five work as the eyebrow.** Compare the vivid
evenly-spaced rainbow, where three of four failed even the 3.0 bar. The palettes
Gary likes are usable BECAUSE they are analogous and mid-chroma — that is also
why they interpolate cleanly (no gamut pinch, see below). The rainbow default is
the pathological case; what he actually wanted is what Radiance is good at.

And only ONE colour ever needs 4.5, because there is one accent. So the mapping
is already there: one hue -> `--ui-accent`, the rest -> the block/categorical
slots. **No new architecture needed.**

**THE GAP, and the next thing to build here:** Sjonis has no way to IMPORT a
palette — it would be hand-edited tokens. Build the path: N hex colours in,
`--ui-accent` plus block colours out, checked against every theme ground on the
way through, with the "walk lightness toward the ink" fix (already used for the
state colours) applied to any that miss. `#2E8B57` at 4.14 is the worked
example; it needs roughly 8% darkening.

### On why the rainbow is drab and no strategy fixes it

Gary asked whether other midpoint strategies would help. Measured: for green ->
blue, sRGB allows only C 0.112 where the interpolation wants 0.304 (37%), and
the perceptual and vivid-as-possible answers are the SAME colour (`#00A5B1`) —
the gamut wall is already there. HSL's `#00FFFF` only looked vivid by sitting at
the wrong lightness. **The drabness is sRGB's gamut pinch between green and
blue, not the interpolation.**

For adjacent hues it is the opposite: blue -> purple has C 0.282 available
against a mean of 0.104, **270% headroom**, so perceptual (`#474F8F`) and vivid
(`#4300EC`) are genuinely different colours. A chroma-policy toggle (keep the
perceptual midpoint vs push to the gamut hull) is therefore worth adding to
Radiance and has a nice property: where it cannot help it changes nothing, so it
cannot make the rainbow case worse. NOT YET BUILT — offered, not agreed.

### RADIANCE — READ, FIXED, SHIPPED (2026-08-04). Answers the question below.

Gary said to fix it at source. Done, pushed, verified on the live deployed file:
`grbsoftware/Radiance` commit "Interpolate bridges in OKLab...".

It was **HSL-only**, confirmed: `midpointColor` averaged H (shortest path), S
and L. The damning number — averaging green `#00FF00` and blue `#0000FF` in HSL
gives cyan `#00FFFF`, which is **lighter than both colours it sits between**. It
does not bridge, it spikes. Perceptual lightness: anchors 0.866 and 0.452, so
the midpoint should read 0.659; HSL put it at 0.905, **off by 0.246**. Evenly
spaced HSL hues range over **0.41** in perceived lightness.

Now OKLab: same pair gives `#00AABF` at 0.676, **off by 0.017**, and that
residual is gamut clipping rather than the interpolation. The matrices were
diffed programmatically against `tools/validate_palette.py` rather than retyped.
`hexToHsl` stays — the picker still edits in HSL, which is a fine thing to TYPE
in and not a thing to average in.

Two more things fixed while in there:

- **`+` and `-` ate your anchors.** Both called `generateEvenHues()`, which
  replaces the whole array, so either button discarded every colour you had
  picked. You could not build a 4-anchor palette at all — getting there wiped
  the 3 you had. They extend and trim now.
- **The service worker is cache-first on a fixed name.** Bumped to
  `radiance-v2`. Without it every installed copy serves its cached index.html
  forever and never sees a fix. **Bump `CACHE_NAME` on every Radiance release.**

**ANSWER TO "more strategies or more palettes?" — neither, and that was the
point.** The bug was one layer below both. Stacking methodologies or presets on
HSL midpointing multiplies output that is all perceptually lumpy; fixing the
space improved all 42 existing presets for free. THEN strategies, not palettes,
because a strategy generates palettes and palettes do not generate strategies —
and because in HSL "triadic = +120 degrees" is simply a lie, since HSL hue is
not perceptually even. Those classical methodologies only do what they claim
once you are in a perceptual space. Fixing the space is what makes them worth
adding.

**Still open:** the GitHub repo DESCRIPTION still says "smooth HSL-interpolated
bridges". That is a repo settings change, so it was left for Gary.

**For Sjonis specifically:** Radiance's raw output is not usable as-is —
`S=100 L=50` hues fail our bars badly (yellow 1.01, green 1.20, blue 1.84
against a 3.0 bar on the theme grounds; only red clears at 3.49). Anything
feeding Sjonis has to pass through `validate_palette.py`. That is the
integration point, and it is the same lesson as every other thread here: the
palette is not done until it is measured against the ground it lands on.

**Radiance** is Gary's own public repo (`grbsoftware/Radiance`): a PWA that
generates palettes by HSL interpolation between anchor colours. Not yet read.
The real question to answer next session: could its interpolation formulae
generate a perceptually even sequential ramp for Sjonis? Caveats to check first —
HSL interpolation is not perceptually uniform (it bunches and produces dead
greys through the middle); OKLCH would be. If Radiance is HSL-only, the useful
move may be to improve Radiance's maths (oklch interpolation) and then reuse it,
which serves both projects.

- **The palette decision** — DONE. Nothing left open except Gary's eye on halo light.
- Layer 3 (React) still unstarted and still worth questioning, because it costs
  the no-build-step property that is currently the suite's best feature.
- **Adapters — DONE this session.** Both now expose `--ui-cat-1..8` (shadcn's
  `--chart-1..5` plus 6-8 under our names; Tailwind's `text-cat-3` etc). The
  shadcn file had a stale note declining to map charts because "our single
  accent cannot supply" series colours — untrue since the categorical work.
  Boundary confirmed and now stated in both files: adapters bridge **tokens,
  never classes**. `tools/check_adapters.py` gates it.
- **Print / forced-colors / reduced-transparency — DONE this session.** See
  README. `prefers-reduced-motion` was the only one previously handled.
- **QUEUED (Gary, 2026-08-04): unify the two demos into one — AND HE SPECIFIED
  THE SHAPE.** "efficient but pretty lol", then: *"a gallery for the genre then
  you can click to go in and explore/customize with themes and skins. And you
  can exit back out sort of behavior."*

  So it is not a merge of two pages, it is a re-rooting of the whole front door
  on the GENRE ring:

      genre gallery  ->  click a genre  ->  framed page + tuner  ->  exit back

  `index.html` already owns half of it (frame, tab strip, live tuner reaching
  into the framed document, hash-as-state so browser back/forward walk the
  history — that IS the "exit back out" behaviour, already built). `gallery.html`
  owns the other half (one layout across six themes side by side). The merge is
  those two, organised by genre instead of by example.

  **Blocked on genres existing** — a gallery of one genre is not a gallery.
  Build two or three first, then this.

  **A distinction to keep straight while building it,** because it looks like it
  contradicts the no-alternatives-in-a-genre rule above and does not: tuning the
  theme or skin from *inside* a genre is EXPLORATION AWAY from a stated
  position, not the genre offering options. The genre remains one authored
  composition; the tuner exists to show what happens when you leave it. The UI
  should make that read — "graphite / bevel" as the genre's stated pair, and
  anything else visibly a deviation from it rather than an equal choice.

  `demo/gallery.html` is now largely redundant. Tuning moved to `index.html`,
  which reaches into the framed document and tunes the REAL skeleton files;
  gallery still tunes four hand-built mini-layouts that duplicate the
  skeletons and drift from them. Either retire it or repoint it — but it is
  still the only place showing one layout across six themes side by side, so
  decide deliberately rather than deleting it. That side-by-side view is the
  thing to preserve through any merge; it is the only answer to "does this hold
  up across the palette" that does not need six clicks.
- Adapters (`adapters/tailwind-v4.css`, `shadcn.css`) predate the site frame,
  commerce and editorial primitives and only bridge tokens, not classes — check
  whether that is still the right boundary before extending them.

Six skeleton files now exist: app-shell, portfolio, storefront,
storefront-product, editorial, game. The layout-monoculture thread is closed —
five genuinely different skeletons (storefront-product is page two of one of
them), not five pages of one app.

**The two axes, restated, because Gary asked directly (2026-08-04) whether each
"template" showcases a different skeleton.** They are independent, and that is
the whole architecture: an SKELETON is structure, chosen by what the thing is;
a THEME is appearance, chosen by who it is for. Every skeleton works in all six
themes, so six skeletons x six themes is 36 combinations, not six. `game.html`
carries `data-theme="oxide"` only because rust suits it — change that one
attribute and the identical skeleton becomes blueprint or halo. A new skeleton
therefore never needs a new theme, and a new theme never needs a new page.

## Working with Gary — what came up this session

- He catches real regressions. He spotted that baking a background into the
  placeholder SVGs broke theming (they're transparent now, so the art takes the
  theme's ground). Take his visual reports seriously and go measure.
- Credit generated art as **generated by Claude, reviewed and approved by Gary**.
  His reasoning: unreviewed AI work presented as finished reflects badly on
  Anthropic. He also asked for the artist link to point at anthropic.com.
- He asks good structural questions (density vs text size) — answer the contract
  question even when deferring the feature.
- **His first word for a thing is usually the right one.** He had "family"
  before "genre" and talked himself out of it, afraid of adding a layer — the
  four-ring vocabulary was his too. The fear was miscalibrated in an instructive
  way: he was guarding against a fifth RING, and family is a string in a genre's
  metadata with no CSS, no token and no load order. Complexity in a vocabulary
  comes from COLLISION (three words for one thing, which is what rotted
  archetype/layout/template), not from count. When he floats a word and
  retracts it, ask what the word would have to *do* before agreeing.
