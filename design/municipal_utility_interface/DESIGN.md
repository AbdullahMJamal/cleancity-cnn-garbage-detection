---
name: Municipal Utility Interface
colors:
  surface: '#f8faf6'
  surface-dim: '#d9dad7'
  surface-bright: '#f8faf6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f0'
  surface-container: '#edeeeb'
  surface-container-high: '#e7e9e5'
  surface-container-highest: '#e1e3df'
  on-surface: '#191c1a'
  on-surface-variant: '#404943'
  inverse-surface: '#2e312f'
  inverse-on-surface: '#f0f1ed'
  outline: '#707972'
  outline-variant: '#c0c9c0'
  surface-tint: '#2e694b'
  primary: '#00442a'
  on-primary: '#ffffff'
  primary-container: '#1f5c3f'
  on-primary-container: '#94d2ad'
  inverse-primary: '#96d4af'
  secondary: '#196c40'
  on-secondary: '#ffffff'
  secondary-container: '#a1f1b9'
  on-secondary-container: '#1f7044'
  tertiary: '#583200'
  on-tertiary: '#ffffff'
  tertiary-container: '#784600'
  on-tertiary-container: '#ffb669'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#b1f1ca'
  primary-fixed-dim: '#96d4af'
  on-primary-fixed: '#002112'
  on-primary-fixed-variant: '#115135'
  secondary-fixed: '#a4f4bc'
  secondary-fixed-dim: '#88d7a1'
  on-secondary-fixed: '#00210f'
  on-secondary-fixed-variant: '#00522c'
  tertiary-fixed: '#ffdcbd'
  tertiary-fixed-dim: '#ffb86e'
  on-tertiary-fixed: '#2c1600'
  on-tertiary-fixed-variant: '#693c00'
  background: '#f8faf6'
  on-background: '#191c1a'
  surface-variant: '#e1e3df'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-uppercase:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.06em
  label-tabular:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
  code-coordinate:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: -0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.75rem
  gutter-desktop: 1rem
  margin: 1rem
  margin-desktop: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system establishes an unyielding, high-density operational platform for civic oversight, waste management logistics, and municipal field triage. It rejects ornamental trends, decorative skeuomorphism, cartoonish civic illustration, and soft consumer abstractions in favor of direct, utilitarian clarity.

The aesthetic fuses the typographic restraint and uncompromising accessibility of **GOV.UK**, the mechanical density and key-driven productivity of **Linear**, and the tabular precision of the **Stripe Dashboard**. The interface must evoke institutional trust, relentless administrative accountability, and urgency without panic. The emotional response is one of operational readiness: dense data presented with such architectural precision that municipal dispatchers and field supervisors can parse hundreds of incidents, route schedules, and fleet vectors instantly.

## Colors

The system uses a calibrated, high-contrast light utility palette constructed specifically for long operating shifts under ambient sun or fluorescent dispatch rooms:

- **Canvas & Surfaces:**
  - Base Canvas: `#FAFAF9` (near-white, low-glare warm gray)
  - Surface/Card/Row Container: `#FFFFFF` (crisp white)
  - Elevated / Interactive Layer: `#F5F5F4` (subtle hover state)
  - Active / Selected Layer: `#EFEFEF`
- **Structural Boundaries:**
  - Standard Border: `1px solid #E5E5E3`
  - Subtle Dividing Line: `1px solid #F0F0EE`
  - Focus Ring: `2px solid #1F5C3F` with an intentional `1px` white offset
- **Typography & Icons:**
  - Primary Text: `#1C1F1D` (deep charcoal, strict contrast ratio > 11:1)
  - Secondary / Muted Text: `#6B706C` (technical context, metadata, units)
  - Disabled Text: `#9CA09D`
- **Operational Accents & Actions:**
  - Primary Accent: `#1F5C3F` (deep forest green; strictly reserved for primary CTA controls, active tab indicators, and functional links)
  - Accent Hover: `#174630`
- **Status Telemetry System (Dots, Badges, Metrics):**
  - **Critical / Danger High:** `#B3261E` (soft-tint background: `#FDF2F2`, border: `#F8B4B4`)
  - **Warning / Medium Priority:** `#B26A00` (soft-tint background: `#FFF8E1`, border: `#FFE082`)
  - **Resolved / Cleaned:** `#2E7D4F` (soft-tint background: `#EDF7ED`, border: `#A5D6A7`)
  - **Pending / Inactive / Muted:** `#6B706C` (soft-tint background: `#F4F4F3`, border: `#E0E0DE`)

## Typography

The typography hierarchy is intentionally compact and functional. It prioritizes rapid optical parsing of telemetry, density of data tables, and minimal eye strain over expressive flair.

- **Typefaces:**
  - Primary UI & Prose: **Inter**
  - Telemetry, Hardware IDs, GPS Coordinates, Timestamp Arrays: **JetBrains Mono**
- **Numeric Rules:**
  - All numerical counts, tonnage amounts, ledger entries, and durations must mandate `font-variant-numeric: tabular-nums lining-nums`.
- **Section & Column Hierarchy:**
  - All table headers, inspection status categorizers, and panel metadata labels must use `label-uppercase` styled with CSS `text-transform: uppercase`.
- **No Decorative Headline Scaling:**
  - Titles do not exceed `24px` on desktop and scale to `20px` on mobile, keeping maximum screen estate dedicated to immediate spatial data, incident queues, and triage controls.

## Layout & Spacing

The layout is grounded in a rigorous, mathematical 8px base rhythm with 4px sub-grid increments for dense micro-components:

- **Layout Grid Models:**
  - **Desktop (>= 1280px):** Fixed left navigation rail (`240px` or collapsed to `56px`), flexible multi-column triage layout, or full-width data table canvas with a 12-column subgrid. Gutters are fixed at `16px` (`space-lg`) to preserve information compactness.
  - **Tablet (768px - 1279px):** Adaptive 8-column layout with split triage/map view toggled via segmented controls. Margin is `16px`.
  - **Mobile (< 768px):** Single-column stacked data feed with pinned primary bottom actions. Outer horizontal canvas margins are constrained strictly to `12px` to maximize data width.
- **Rhythm Rules:**
  - Component padding must never exceed `space-lg` (`16px`).
  - Table cells adhere strictly to a dense `8px` vertical by `12px` horizontal padding standard.
  - Gaps between metadata key-value pairs are locked at `space-xs` (`4px`) and `space-sm` (`8px`).

## Elevation & Depth

This system operates on a zero-shadow, mechanical plane. Hierarchy is achieved solely through **tonal layering and crisp 1px structural borders**. 

- **Surface Tiers:**
  - **Level 0 (Canvas):** `#FAFAF9` — default window and application foundation.
  - **Level 1 (Panels & Cards):** `#FFFFFF` framed by a `1px solid #E5E5E3` boundary.
  - **Level 2 (Dropdowns, Command Menus, Modals):** `#FFFFFF` bordered with `1px solid #D4D4D1`, elevated by an ultra-subtle utility drop shadow: `0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)`.
- **Prohibitions:**
  - Strictly no diffuse, colored ambient glow shadows.
  - Strictly no backdrop blur filters, frosted glass layers, or skeuomorphic gradient overlays.
  - Highlighting is handled via crisp 1px borders shifting to `#1F5C3F` or fill shifts to `#F5F5F4`.

## Shapes

The geometric form language is strict, squared, and sober:

- **Base Corner Radius:** `roundedness: 1` (`0.25rem` / `4px`) applied across buttons, inputs, badge tags, and table cells.
- **Outer Shell & Modals:** Maximum border-radius of `6px` (`rounded-md`).
- **Telemetry Indicators:** Status dots are standard geometric circles (`border-radius: 9999px`) sized at `6px` or `8px` fixed squares with rounded sub-pixels.
- **Prohibitions:** Pill-shaped (`rounded-full`) filter chips and large squircular card corners are forbidden. Every element must look engineered and modular.

## Components

### Buttons
- **Primary:** Background `#1F5C3F`, text `#FFFFFF`, border `1px solid #1F5C3F`. Hover `#174630`. Focus `2px` ring `#1F5C3F` with `1px` white gap.
- **Secondary / Neutral:** Background `#FFFFFF`, text `#1C1F1D`, border `1px solid #E5E5E3`. Hover `#F5F5F4`.
- **Destructive:** Background `#FFFFFF`, text `#B3261E`, border `1px solid #F8B4B4`. Hover `#FDF2F2`.
- **Sizing:** Dense default height `32px` (horizontal padding `12px`, font size `13px`, weight `500`). Micro height `26px` for inline table row triggers.

### Chips, Tags & Badges
- Non-interactive status tokens: 
  - Height `20px`, padding `0 6px`, font size `11px`, weight `500`, border radius `4px`.
  - Pair status dot (`6px` circle) with a label.
  - Critical: background `#FDF2F2`, border `1px solid #F8B4B4`, text `#B3261E`.
  - Warning: background `#FFF8E1`, border `1px solid #FFE082`, text `#B26A00`.
  - Cleaned: background `#EDF7ED`, border `1px solid #A5D6A7`, text `#2E7D4F`.
  - Pending: background `#F4F4F3`, border `1px solid #E0E0DE`, text `#6B706C`.

### Form Inputs & Selects
- Background `#FFFFFF`, border `1px solid #E5E5E3`, border radius `4px`.
- Text `#1C1F1D`, placeholder `#6B706C`.
- Height `32px`, horizontal padding `8px`, font size `13px`.
- Hover border `#D4D4D1`. Focus border `#1F5C3F` with zero blur outline.
- Monospace mode: For coordinate entries (`lat, lng`) and vehicle unit IDs, swap input font to `JetBrains Mono` at `12px`.

### Checkboxes & Radio Controls
- Dimensions `14px x 14px`, border `1px solid #D4D4D1`, radius `3px` (radios `9999px`).
- Checked state: background `#1F5C3F`, border `#1F5C3F`, check icon `#FFFFFF` stroke `2px`.

### Data Tables & Incident Lists
- Fixed header with background `#FAFAF9`, bottom border `1px solid #E5E5E3`. Headers styled with `label-uppercase` text in `#6B706C`.
- Rows: background `#FFFFFF`, bottom border `1px solid #F0F0EE`. Hover background `#F5F5F4`. Selected row background `#F0F4F2`.
- Cell height `36px`, cell padding `6px 12px`.
- Tabular numeric alignment: numbers, dates, coordinates right-aligned with `font-variant-numeric: tabular-nums`.

### Cards & Metrics Panels
- Background `#FFFFFF`, border `1px solid #E5E5E3`, radius `6px`.
- Padding `12px 16px`. Header features upper-case label, secondary metric, followed by a primary numeric readout (`20px` semibold, tabular).

### Domain-Specific Components
- **GIS Coordinate Block:** Padded inline badge (`2px 6px`) in `#F4F4F3`, displaying `lat, lng` in `JetBrains Mono` `12px` text, copyable on hover.
- **Triage Priority Matrix Pill:** Micro split-badge with priority ranking (`P0` through `P3`) color-coded to the telemetry status system.
- **Iconography Standard:** Lucide icons with stroke width locked to `1.5px` (thin-stroke utility profile) at `14px` or `16px` bounding boxes.