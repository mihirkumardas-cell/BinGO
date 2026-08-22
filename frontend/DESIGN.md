---
name: CleanTrack AI Industrial System
colors:
  surface: '#161B22'
  surface-dim: '#10141a'
  surface-bright: '#353940'
  surface-container-lowest: '#0a0e14'
  surface-container-low: '#181c22'
  surface-container: '#1c2026'
  surface-container-high: '#262a31'
  surface-container-highest: '#31353c'
  on-surface: '#dfe2eb'
  on-surface-variant: '#becaba'
  inverse-surface: '#dfe2eb'
  inverse-on-surface: '#2d3137'
  outline: '#899485'
  outline-variant: '#3f4a3d'
  surface-tint: '#7bdb80'
  primary: '#7bdb80'
  on-primary: '#00390e'
  primary-container: '#238636'
  on-primary-container: '#f9fff3'
  inverse-primary: '#006e23'
  secondary: '#aac7ff'
  on-secondary: '#002f65'
  secondary-container: '#0072e3'
  on-secondary-container: '#fefcff'
  tertiary: '#ffb1c4'
  on-tertiary: '#65012e'
  tertiary-container: '#bf4d72'
  on-tertiary-container: '#fffbff'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#97f999'
  primary-fixed-dim: '#7bdb80'
  on-primary-fixed: '#002106'
  on-primary-fixed-variant: '#005319'
  secondary-fixed: '#d7e3ff'
  secondary-fixed-dim: '#aac7ff'
  on-secondary-fixed: '#001b3e'
  on-secondary-fixed-variant: '#00458e'
  tertiary-fixed: '#ffd9e1'
  tertiary-fixed-dim: '#ffb1c4'
  on-tertiary-fixed: '#3f001a'
  on-tertiary-fixed-variant: '#841e45'
  background: '#10141a'
  on-background: '#dfe2eb'
  surface-variant: '#31353c'
  surface-raised: '#21262D'
  border: '#30363D'
  success: '#3FB950'
  warning: '#D29922'
  danger: '#DA3633'
  text-primary: '#E6EDF3'
  text-secondary: '#8B949E'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.03em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '700'
    lineHeight: '1.3'
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.4'
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 24px
  sidebar-width: 240px
  control-touch-target: 44px
---

## Brand & Style

The design system for CleanTrack AI is rooted in a **High-Utility Industrial** aesthetic. It is a mission-critical tool designed for both high-stress field operations and high-density municipal oversight. The brand personality is authoritative, precise, and resilient—evoking the feeling of a sophisticated command center rather than a consumer social app.

The visual direction follows **Modern Industrial Minimalism** with a **Dark-Mode First** constraint. This minimizes eye strain during low-light field use and allows high-urgency color signals (Action Green, Amber, Red) to pop with maximum contrast. The UI utilizes a "glass-on-metal" approach: dark, matte surfaces paired with crisp, luminous data overlays and subtle depth to indicate interactivity.

**Key Principles:**
- **Map-Centricity:** The map is the primary workspace; all UI elements should feel like tactical overlays.
- **Utility over Decoration:** Every border, shadow, and icon must serve a functional purpose in data density.
- **Urgency-Driven Contrast:** Use the "Action Green" for progress and "Danger Red" for critical alerts against the deep charcoal backdrop.

## Colors

The palette is optimized for a **Dark-First** environment. The background (`#0D1117`) provides a deep, non-distracting canvas. 

- **Primary (Action Green):** Used for "Clean" brand actions, successful analysis, and primary CTA buttons.
- **Secondary (Accent Blue):** Used for links, informational icons, and secondary navigational elements.
- **Functional Spectrum:** A strict three-tier urgency system:
    - **Critical/Hazardous:** `#DA3633` (Red)
    - **Medium Urgency:** `#D29922` (Amber)
    - **Resolved/Stable:** `#3FB950` (Green)
- **Neutral Tiering:** Use `Surface` for cards and `Surface-raised` for modals or active states to create a clear hierarchy of information without relying on heavy shadows.

## Typography

Typography focuses on immediate legibility and data density. 

- **Inter** is the primary typeface, chosen for its neutral, professional tone and exceptional readability at small sizes. 
- **Headings** utilize tight tracking (`-0.02em` to `-0.04em`) and heavy weights to create a sense of industrial urgency.
- **JetBrains Mono** is reserved for technical data: report IDs, GPS coordinates, AI confidence percentages, and timestamps. This font choice signals "raw data" to the user.
- **Mobile Adjustments:** For mobile views, `headline-xl` should scale down to `28px` to ensure map overlays do not obscure the primary content.

## Layout & Spacing

The layout is a **Hybrid Map-Centric Grid**. 

- **Citizen App:** A fluid, mobile-first layout. The map sits as the background layer, with floating cards and bottom sheets handling the reporting flow. 
- **Admin Dashboard:** A fixed-sidebar layout (240px). The main content area is a "Workbench" that can toggle between a full-screen map and a dense data table.
- **Spacing Rhythm:** Based on a 4px baseline grid. Use 16px (4 units) for standard component gutters. 
- **Data Density:** In the admin table view, reduce vertical padding to 8px to maximize information per screen (Data Density principle).
- **Touch Targets:** All interactive elements in the citizen app must maintain a minimum 44px height/width for field usability.

## Elevation & Depth

Elevation is achieved through **Tonal Layering** and **Low-Contrast Outlines** rather than heavy shadows, to maintain the "Industrial" look.

- **Level 0 (Background):** `#0D1117` - The map or main app canvas.
- **Level 1 (Surface):** `#161B22` - Cards, navigation bars, and side panels.
- **Level 2 (Raised):** `#21262D` - Hover states, modals, and active map-overlay controls.
- **Outlines:** Every surface at Level 1 or higher must have a 1px solid border of `#30363D` to define its boundaries against the dark background.
- **Shadows:** Use a single "Ambient Glow" shadow for high-urgency alerts (Urgency Score > 80). The shadow should use the color of the urgency level (e.g., a faint red glow) with a 12px blur and 0.3 opacity.

## Shapes

The shape language is **Soft-Industrial**. We avoid perfectly sharp corners to maintain a modern software feel, but avoid overly rounded "bubbly" shapes to keep the professional utility tone.

- **Standard Elements:** 0.25rem (4px) radius for buttons, input fields, and small cards.
- **Large Containers:** 0.5rem (8px) for side drawers and main dashboard panels.
- **Pills:** Used exclusively for status indicators (e.g., "Dispatched", "Resolved") to differentiate them from functional buttons.

## Components

### Urgency Score Gauges
A semi-circular arc meter. The arc fills based on the score (0-100). The color of the fill must dynamically change based on the Urgency Level colors (Green -> Amber -> Red). The center of the arc displays the numerical score in `label-mono`.

### Waste Type Badges
Small, dark-filled pills (`#21262D`) with a 1px border. They contain a waste-specific icon (e.g., 📦) followed by the type name in `label-sm`.

### Timeline Tracking
A vertical "Stepped" list. Active steps use a solid Action Green dot with a pulse animation. Completed steps use a checkmark. Pending steps use a hollow border (`#30363D`).

### Map-Overlay Controls
Floating circular or slightly rounded square buttons. Background: `#161B22` (80% opacity with a background blur). Icon color: `#E6EDF3`.

### Admin Data Tables
- **Header:** Sticky header with `#21262D` background.
- **Rows:** Alternating subtle zebra striping or 1px bottom border.
- **AI Confidence Indicators:** A small horizontal bar within a cell. The bar length represents the percentage, and the color fades from Gray (Low) to Action Green (High).

### Input Fields
Dark background (`#0D1117`), 1px border (`#30363D`). On focus, the border transitions to `Accent Blue` or `Action Green` with a subtle outer glow.