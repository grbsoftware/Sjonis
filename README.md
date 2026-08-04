# Sjonis

**[See it running →](https://grbsoftware.github.io/Sjonis/)** — every example in one
frame, arrow keys to move between them, one toggle for light and dark.

A token-driven set of interface templates. Two axes that move independently:

- **Archetype** — structure. Chosen by what the thing *is*.
- **Theme** — appearance. Chosen by who it is *for*.

Any archetype works with any theme, because archetypes contain no colour, size or
typeface. They reference tokens; themes supply values. That is the whole idea, and
every rule below exists to keep it true.

No build step, no dependencies, no framework. Two stylesheets and HTML — plus one
optional script if you want the parts that move.

```
index.html           example browser — every page below in one frame
core/ui.css          structure, primitives, components — contains no colours
core/themes.css      six themes, each with a light and a dark palette
core/ui.js           optional behaviour layer — see below
tokens/              the same themes as W3C DTCG JSON — the portable source
tools/               token extractor + generators + contrast validator (Python, no deps)
adapters/            bridges to Tailwind v4 and shadcn/ui
archetypes/          copyable page scaffolds — app-shell, portfolio
dist/                generated: GTK4 CSS, WinUI/WPF XAML
demo/gallery.html    live theme switcher + tuner + CSS export
demo/behaviour.html  every interactive component, switchable across all themes
.claude/skills/      Claude Code skill so an agent can use the suite directly
```

Nothing to install and nothing to build. Clone it, open `index.html`, and every
example runs — the whole suite is HTML, CSS and one optional classic script.

## Quick start

```html
<html data-theme="vanilla" data-mode="light">
  <link rel="stylesheet" href="core/ui.css" />
  <link rel="stylesheet" href="core/themes.css" />
  <body class="ui">
    <!-- copy an archetype from archetypes/ -->
  </body>
</html>
```

`class="ui"` is required on whichever element should carry the ground and font — it
can be `<body>` or any wrapper, which is how the demo previews a theme inside an
otherwise unthemed page.

`data-mode` is optional. Omit it and the theme's preferred mode applies.

## The behaviour layer

The stylesheets can *show* a menu; they cannot open one. Add the script last and
behaviour attaches itself from data-attributes — no init call, no bundler, no
dependency:

```html
<button class="ui-btn-ghost" data-ui-menu="#actions">Actions</button>
<div class="ui-menu" id="actions">
  <button class="ui-menu-item">Restart</button>
</div>
<script src="core/ui.js"></script>
```

Dialogs, menus, tabs, accordions, toasts, tooltips, sortable tables, live
filtering, clipboard, form validation, a command palette, and runtime theme and
density switching. `demo/behaviour.html` exercises all of it.

Three choices worth stating, because they are the ones usually made the other
way. It is a **classic script, not an ES module** — modules are blocked on
`file://`, and opening a single .html by double-clicking it has to keep working.
It **uses the platform**: `<dialog>` for modals, `<details>` for accordions, the
constraint-validation API for forms, because each of those is a focus trap or a
state machine that hand-rolled versions get subtly wrong. And it **degrades** —
delete the file and dialogs stay closed, tab panels render stacked, and forms
fall back to native validation. Nothing becomes unreadable.

## Free lazy loading

Gallery plugins charge for this; it is thirty lines. Put `data-ui-lazy` on a frame:

```html
<div class="ui-frame ui-ratio-square" data-ui-lazy>
  <img data-src="work/01.jpg" alt="Grid Study 01">
</div>
```

The deferral itself is one native attribute and is set for you. What the script
adds is the part that actually costs work: the box is reserved before the image
exists so nothing jumps, a shimmer holds the space, the swap is a fade, a failed
image stops animating instead of shimmering forever — and a **cached image does
not fade**, because a flicker every time you scroll back is worse than no
animation at all.

Use a plain `src` and it still works with JavaScript off; `data-src` defers the
request until a screen away, which saves more bandwidth but needs the script.

## Themes

| Theme | Character | Reach for it when |
|---|---|---|
| `vanilla` | Neutral but designed | Default. Undefined audience, or you are handing this to someone else. |
| `blueprint` | Square, monospace, cyan | Developer tools, infrastructure, expert operators. |
| `halo` | Translucent, mint, generous | Consumer-facing and modern. Not for dense data. |
| `graphite` | Cool near-monochrome | Internal tools used all day; should recede. |
| `oxide` | Rust, heavy, tight | Trades, hardware, manufacturing, logistics. |
| `vellum` | Bone, serif, airy | Content, research, documentation, reports. |

Choosing one is a real decision, not a coin flip — see
[`.claude/skills/ui-suite/references/palettes.md`](.claude/skills/ui-suite/references/palettes.md),
which also explains why this suite encodes *category convention* rather than "colour
psychology."

## Customising

Three levels, cheapest first. Most projects never get past the first.

### 1. Override tokens

Load after `themes.css` and change values. Nothing else.

```css
/* Blueprint, but the client's brand is amber. */
[data-theme="blueprint"][data-mode="dark"]{
  --ui-accent:       #F0A63C;
  --ui-accent-hover: #FFBC52;
  --ui-accent-ink:   #0B0E12;   /* dark ink — amber is a light accent */
}
```

`demo/gallery.html` generates exactly this block for you: tune the controls, copy the
output. It computes the hover shade and picks the ink colour by luminance, which is
the part people get wrong.

Density is a single number. `--ui-density: 1.25` makes the entire interface roomier;
`0.9` makes it compact. No component padding is touched.

### 2. Author a theme

Copy the `vanilla` block in `core/themes.css` and change values, not structure. The
split matters:

- **base block** — shape, type, density. Mode-independent.
- **mode blocks** — colour only.

Repeat your preferred mode's colours in the base block so `data-theme` works without
`data-mode`.

Verify before shipping: body text ≥ 4.5:1 on its own surface, borders and large text
≥ 3:1, state distinguishable in greyscale, semantic colours independent of the accent,
and *both* modes actually designed rather than inverted.

### 3. Extend the contract

Only if no existing token can express what you need. Add it to the `:root` block in
`ui.css` **and give every theme a value for it.** A token that only some themes define
is a bug that surfaces as one theme looking broken.

## Rules

These are what keep the two axes independent. Break them and the suite degrades into
six copies of the same stylesheet.

- **Never hardcode a colour, radius, font or spacing value in an archetype.**
- **Semantic colour is not the accent.** `--ui-good/warn/crit` stay independent so a
  rebrand cannot silently change what "failed" means.
- **State needs a non-colour cue.** Pills carry a dot and a border, not just a hue —
  which is what makes them survive greyscale and colour-blindness.
- **Three text levels only.** `--ui-text`, `--ui-text-dim`, `--ui-text-faint`. People
  cannot reliably distinguish a fourth, so a fourth is not hierarchy, it is noise.
- **Wide content scrolls itself.** Wrap tables in `.ui-scroll`. The page body must
  never scroll sideways.

## Fonts

Everything uses system font stacks, ordered Windows-first (Segoe UI, Cascadia Mono,
Georgia). No webfonts, no network requests, no layout shift, nothing to license.

If you want a distinctive typeface, override `--ui-font` / `--ui-font-display` and
load the face yourself. Only those two tokens need to change.

`tokens/fonts.json` is a curated shortlist with reasoning attached. The whole
Google Fonts library is also catalogued, because cataloguing is nearly free and
bundling is what costs bytes — those are different questions:

```bash
python tools/fonts.py fetch                                  # 1,942 families
python tools/fonts.py find --category mono --variable --max-kb 200
python tools/fonts.py find --category serif --subset greek --sort popularity
python tools/fonts.py show Inter
```

It records only what is checkable — weights, variable axes, subsets, file size,
designers, dates. It records **no** opinion on x-height, personality or
legibility: those are judgments or measurements of the binary, and a guess
written into a data file becomes a fact three months later. Set the font in the
tuner and look at it.

## Checking a theme

```bash
python tools/validate_palette.py        # every theme x mode, WCAG 2.1
python tools/validate_palette.py halo   # one theme
python tools/validate_palette.py -v     # show passes too
```

It measures the pairings the CSS actually produces rather than plausible-looking
ones, and composites translucent tokens over their ground first — halo's surfaces
are `rgba()`, so a ratio against the literal value is meaningless. Exit code is 1
on any required failure, so it can gate a commit.

## Beyond the web

The tokens are the bones; CSS is one skin. The same theme values compile to
desktop toolkits, so a Windows or Linux app can wear the same design without
sharing a line of CSS.

```bash
python tools/build_themes.py verify   # round-trip check, run this after editing
python tools/build_themes.py all      # emit every target into dist/
```

| Target | Reuse | How |
|---|---|---|
| **Tauri / Electron** | Total | It is a browser. Use `core/*.css` unchanged. |
| **GTK4** (Linux) | High | GTK **4.16+** supports CSS custom properties and `var()`. `dist/gtk/` holds the token block; write widget rules against GTK selectors. |
| **WinUI 3 / WPF** | Medium | `dist/xaml/` — `Color` + `SolidColorBrush` resources, `rgba()` converted to `#AARRGGBB`. |
| **Qt / Flutter / Avalonia** | Medium | Add a generator to `tools/build_themes.py`; the token source already exists. |

`tokens/themes.tokens.json` is [W3C DTCG](https://www.designtokens.org/) format,
which reached its first stable version in October 2025 — so Style Dictionary,
Figma, Penpot and friends can read it directly if you'd rather not use the
Python generators.

## Licence

[PolyForm Noncommercial 1.0.0](LICENSE.md). Free to use, change and redistribute for
any **noncommercial** purpose — personal projects, study, hobby work, and use by
charities, schools, public research, and government bodies.

**Commercial use requires a separate licence.** If you want to use Sjonis in or for a
business — a product you sell, client work, anything with a commercial application —
open an issue at [grbsoftware/Sjonis](https://github.com/grbsoftware/Sjonis/issues) or
contact [@grbsoftware](https://github.com/grbsoftware) to arrange one. Terms are
straightforward and I'd like to hear what you're building.

**Two honest limits.** Composite values (shadows, gradients, blur) are stored as
raw CSS and only the CSS and GTK targets consume them — depth on Windows is
Mica/Acrylic and ThemeShadow, which is set on the element, not in a resource
dictionary. And translucency is the least portable thing here: `backdrop-filter`
is compositor-dependent on Linux and unreliable in WebKitGTK, which is what Tauri
uses there. **Halo needs a solid-surface fallback outside the browser; Blueprint
travels everywhere unchanged.**

Don't fight the platform. Let brand tokens own accent, semantic colour, density
and radius — and let the OS own window chrome, native dialogs and scrollbars.
Offering "follow system accent" is usually the right default on Windows and GNOME.

## Using it with Tailwind or shadcn/ui

`adapters/` bridges the suite to both without adding a dependency to the core.

- **`tailwind-v4.css`** — an `@theme inline` block. `inline` is load-bearing:
  without it Tailwind bakes values at build time and utilities freeze to whichever
  theme was active when you compiled.
- **`shadcn.css`** — maps our tokens onto shadcn's variables, so all six themes
  restyle every shadcn component.

One trap worth repeating: **shadcn's `--accent` is not the brand colour.** It is
the muted hover surface for menu and command-palette rows; the brand colour is
`--primary`. Map `--ui-accent` onto `--accent` and every hover state in the app
goes neon. The adapter maps `--ui-accent → --primary` and `--ui-surface-3 →
--accent`.

## Using it with Claude Code

`.claude/skills/ui-suite/` makes the suite available as a skill. Ask for a dashboard,
an admin panel, or a restyle and the agent will pick an archetype, justify a theme
against the audience, and copy it in — rather than inventing CSS from scratch each
time.

## Status

Iteration 02. One archetype (`app-shell`), six themes, live tuner.

Next: split view, three-pane, command palette, settings and form states, marketing
page. Each is markup only — no new CSS, because the primitives already exist.
