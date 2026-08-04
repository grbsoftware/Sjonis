# Choosing a palette by audience

## Read this before reaching for "color psychology"

The popular version — blue means trust, red means urgency, green means growth — is
weakly evidenced. Most of it traces to marketing content citing other marketing
content rather than to replicated findings. The mainstream academic position
(Elliot & Maier's *color-in-context* theory is the standard framing) is that colour
meaning is **learned and contextual**, not innate. The same red reads as "error" in
a console, "premium" on a sports car, and "celebration" at a wedding in much of
East Asia.

So do not encode a mood chart. Two mechanisms actually do the work, and both are
things you can verify and defend to a client:

**1. Category convention.** People recognise a category by what its incumbents look
like. Blue-orange-grey reads as *tools* because DeWalt, Fluke, Home Depot and the
hardware aisle trained that expectation over decades — not because orange is
intrinsically energetic. Convention is real and worth using; it is just learned
rather than innate, which means it varies by market and decays over time.

**2. Contrast and role separation.** Blue and orange sit roughly opposite on the
wheel, so blue can hold the calm structural ground while orange carries every hot
role — primary action, warning, live state — without the two ever competing for the
same job. That is a mechanical property. It survives translation and it survives
someone disagreeing with you about feelings.

**The practical rule:** pick the ground from category convention, pick the accent for
role separation against that ground, and verify contrast numerically. Then you can
explain every choice without appealing to vibes.

---

## Presets

Each entry gives the convention it borrows from and the closest shipped theme. These
are starting points to tune, not laws.

### Developer tools / infrastructure
Dark ground, cool hue, monospace present, one high-chroma signal colour.
Convention set by terminals, CI dashboards, Linear, Vercel, Datadog.
Accent should be cyan, green or amber — not blue, which disappears into a dark
blue-grey ground.
→ **`blueprint`**, or **`graphite`** where the tool is used all day and should recede.

### Trades / hardware / industrial
Warm neutrals or near-black, high-visibility accent (orange, amber, safety yellow),
heavier weights, tighter radii, strong borders. Reads as durable rather than delicate.
Legibility in bad conditions matters more than elegance.
→ **`oxide`**.

### Finance / insurance / legal
Conservative, low-chroma, navy or deep green ground, generous whitespace, serif
permitted in display. Restraint signals custody of other people's money. Avoid
translucency and glow — they read as unserious in this category.
→ **`vellum`** for document-heavy work, **`graphite`** for dashboards.

### Healthcare / clinical
Light ground, calm blue-green, very high contrast, no ambiguity in state colour.
Semantic colour must be unmistakable and never reused as the accent. Accessibility
is not optional here — assume tired users on bad monitors.
→ **`vanilla`** with the accent shifted toward teal.

### Consumer / creative / social
Permission to be expressive. Depth, translucency, ambient colour, larger radii,
generous spacing. The risk is illegibility, not blandness.
→ **`halo`**.

### Enterprise SaaS / internal tools
Near-neutral, one restrained accent, density over drama. The interface is a means to
an end and the user did not choose to be there.
→ **`vanilla`** or **`graphite`**.

### Content / research / publishing
Paper-adjacent ground, serif display, low contrast, wide measure, minimal chrome.
Optimised for sustained reading rather than scanning.
→ **`vellum`**.

---

## Verify, don't trust

Any palette you build or tune must clear these before it ships:

- **Body text** ≥ 4.5:1 against its own surface. **Large text and UI borders** ≥ 3:1.
  Check `--ui-text-dim` against `--ui-surface-2` specifically — that pairing is the
  one that usually fails, because both moved from the value you checked.
- **State must survive greyscale.** Screenshot the page, desaturate it, confirm you
  can still tell "failed" from "live". This is why every pill in the suite carries a
  dot and a border, not just a hue.
- **Semantic colour is never the accent.** If "good" and "primary action" are the
  same hue, a rebrand silently breaks meaning. The token contract separates them for
  this reason — keep them separate when you tune.
- **Check both modes.** A palette that only works dark is half a theme.

## Tuning without authoring a whole theme

Most projects need an existing theme nudged, not a new one. Override after the theme
loads:

```css
/* Blueprint, but for a client whose brand is amber rather than cyan. */
[data-theme="blueprint"][data-mode="dark"]{
  --ui-accent:      #F0A63C;
  --ui-accent-hover:#FFBB5C;
  --ui-accent-ink:  #1A1206;   /* re-check: dark ink on a light accent */
  --ui-accent-soft: #2A2010;
}
```

Three tokens and their ink. That is usually the whole job — and it is why the accent
is a token rather than a value baked into forty component rules.
