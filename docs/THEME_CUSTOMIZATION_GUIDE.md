# Theme, Icon & UI Customization Guide

Practical guide for changing colors, icons, fonts, and adding/removing buttons on
specific pages in the FlowMind AI frontend.

> Background: this project uses **Tailwind CSS v4** (config-less — everything lives
> in [`app/globals.css`](../app/globals.css)), **shadcn/ui** for base components
> ([`components/ui/`](../components/ui/)), and **lucide-react** for icons.

---

## 1. Changing the theme color

Color is defined in **two layers**, and you need to touch both for a full rebrand.

### Layer 1 — CSS variables (the "real" theme)

Open [`app/globals.css`](../app/globals.css) and edit the `:root` block (around
line 49). The FlowMind-specific tokens are prefixed `--fm-*`:

```css
:root {
  /* Primary: Dark Blue */
  --fm-primary:        #1D4ED8;   /* main brand color */
  --fm-primary-light:  #2563EB;
  --fm-primary-dark:   #1E3A8A;
  --fm-primary-glow:   rgba(29, 78, 216, 0.35);

  /* Secondary: Light Blue */
  --fm-secondary:      #3B82F6;
  --fm-secondary-light:#60A5FA;

  /* Accent: Emerald */
  --fm-accent:         #10B981;

  /* Warning / Amber, Danger */
  --fm-warning:        #F59E0B;
  --fm-danger:         #EF4444;
  ...
}
```

Change these hex values and everything that references `var(--fm-primary)` etc.
(shadcn tokens like `--primary`, `--ring`, `--sidebar-primary`, plus utility
classes like `.bg-fm-primary`, `.text-gradient-violet`, `.glow-violet`) updates
automatically. There's a matching `.dark { ... }` block just below — update it
too (currently it duplicates `:root` since the app is dark-only).

### Layer 2 — Hardcoded hex values in components (the part people forget)

Most page/component code does **not** use `bg-primary` / `text-primary` — it
uses Tailwind arbitrary values or inline styles with the literal hex baked in:

```tsx
<div className="bg-[#1D4ED8] text-[#3B82F6]" />
<div style={{ color: '#10B981' }} />
```

`#1D4ED8` alone shows up **500+ times** across `components/` and `app/`, so
changing `--fm-primary` in globals.css will **not** recolor most of the UI on
its own. To catch these, find and replace project-wide:

```bash
# find every hardcoded occurrence of the primary blue
grep -rn "#1D4ED8" components/ app/

# do the same for secondary / accent colors
grep -rn "#3B82F6" components/ app/
grep -rn "#10B981" components/ app/
```

Then replace each hex literal with your new color (or better, swap it for the
Tailwind token equivalent — `text-[#1D4ED8]` → `text-primary` — so future
changes only need Layer 1).

**Hottest files** (most occurrences of the primary blue):
- [`components/settings/SettingsView.tsx`](../components/settings/SettingsView.tsx)
- [`components/workflows/WorkflowEditor.tsx`](../components/workflows/WorkflowEditor.tsx)
- [`components/workflows/WorkflowCanvas.tsx`](../components/workflows/WorkflowCanvas.tsx)
- [`components/profile/ProfileView.tsx`](../components/profile/ProfileView.tsx)
- [`components/landing/DocsPreview.tsx`](../components/landing/DocsPreview.tsx)

### Layer 3 — Gradients and glow effects

The `@layer utilities` block in `globals.css` (from line ~193) defines gradient
and glow classes with their own hardcoded stops, e.g.:

```css
.text-gradient-violet {
  background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 50%, #06B6D4 100%);
}
.glow-violet {
  box-shadow: 0 0 20px var(--fm-primary-glow), 0 0 40px rgba(29, 78, 216, 0.15);
}
```

These use a mix of CSS vars and literal hex/rgba — if your new brand color is
very different (e.g. orange instead of blue), edit these gradient stops
directly rather than relying on the variable substitution alone.

> Note: `nexagent-color-palette.json` in the repo root is an **unused design
> doc** for a planned orange rebrand that was never applied — it's not wired
> into any code. Ignore it unless you're intentionally reviving that palette.

### Quick checklist for a full recolor
1. Edit `--fm-*` values in `app/globals.css` `:root` (and `.dark`).
2. `grep -rn "#1D4ED8"` (and secondary/accent hex) across `components/` and `app/`, replace.
3. Check gradient/glow utility classes in `@layer utilities` for extra hardcoded stops.
4. Restart the dev server (`npm run dev`) and eyeball the landing page, dashboard, and workflow editor.

---

## 2. Changing / adding an icon

Icons come from **lucide-react** (general UI) and **simple-icons** (brand logos
like WhatsApp, Slack, OpenAI — under
[`components/icons/brands/`](../components/icons/brands/)).

### Swap an existing icon

Find the component using it, e.g. [`components/landing/Navbar.tsx`](../components/landing/Navbar.tsx):

```tsx
import { Menu, X, Zap, ChevronDown } from "lucide-react";
...
<Zap className="w-5 h-5 text-white" />
```

1. Browse [lucide.dev/icons](https://lucide.dev/icons) for a replacement name (e.g. `Sparkles`).
2. Update the import: `import { Menu, X, Sparkles, ChevronDown } from "lucide-react";`
3. Update the JSX tag: `<Sparkles className="w-5 h-5 text-white" />`

Size and color are just Tailwind classes (`w-5 h-5`, `text-white`,
`text-primary`) — lucide icons inherit `currentColor`, no separate icon config
needed.

### Add a brand logo icon (WhatsApp, Slack, etc.)

Look at an existing one in `components/icons/brands/` for the pattern (SVG
wrapped as a React component using `simple-icons` path data), then register it
wherever brand icons are mapped, e.g.
[`lib/workflow/utils/AuthenticBrandLogos.tsx`](../lib/workflow/utils/AuthenticBrandLogos.tsx).

---

## 3. Adding or removing a button on a specific page

There's no central "button registry" — buttons live directly in each page or
component file. General workflow:

### Removing a button
1. Find the page, e.g. [`app/dashboard/page.tsx`](../app/dashboard/page.tsx) or a
   component it renders under `components/dashboard/`.
2. Locate the `<Button>` (from [`components/ui/button.tsx`](../components/ui/button.tsx))
   or plain `<button>` element and delete it.
3. If it was the only consumer of a handler function (`onClick={handleX}`),
   remove the now-unused handler too — check for other references first with Grep.

### Adding a button
Use the shared shadcn `Button` component for consistency:

```tsx
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react"; // if you want an icon

<Button
  onClick={handleSomething}
  className="bg-primary hover:bg-primary/90 text-white"
>
  <Plus className="w-4 h-4 mr-2" />
  New Item
</Button>
```

- Prefer `bg-primary` / `text-primary` (Layer 1 tokens) over hardcoded hex so
  it stays in sync with future theme changes.
- `Button` supports `variant` (`default`, `outline`, `ghost`, `destructive`,
  etc.) and `size` props — check
  [`components/ui/button.tsx`](../components/ui/button.tsx) for the full list
  instead of hand-rolling styles.

### Finding the right file for a given page
Pages live under `app/<route>/page.tsx` (Next.js App Router). Dashboard-style
pages typically delegate most UI to a matching component in
`components/dashboard/`, `components/settings/`, `components/profile/`, etc.
If unsure which file renders a button you see in the browser, search for its
visible label text with Grep across `components/` and `app/`.

---

## 4. Fonts (bonus — related gap worth knowing)

Fonts are loaded in [`app/layout.tsx`](../app/layout.tsx) via `next/font/google`
(Geist, Geist Mono, Outfit, Inter). Body defaults to `Outfit, Inter, ...`
(set in `globals.css`).

Several landing-page components set
`style={{ fontFamily: 'Montserrat, sans-serif' }}` or `'Poppins, sans-serif'`
inline, but **neither font is actually loaded anywhere** in the project — they
silently fall back to the system default font. To make them render as
intended, add them the same way Outfit/Inter are set up in `app/layout.tsx`:

```ts
import { Montserrat, Poppins } from 'next/font/google'

const montserrat = Montserrat({ variable: '--font-montserrat', subsets: ['latin'] })
const poppins = Poppins({ variable: '--font-poppins', subsets: ['latin'], weight: ['400','500','600','700'] })
```

Then add `${montserrat.variable} ${poppins.variable}` to the `<body className>`
string, and either reference `var(--font-montserrat)` in CSS or keep using the
inline `fontFamily` style (it'll now resolve to the loaded font instead of a
system fallback).
