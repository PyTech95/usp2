# Design Guidelines Blueprint: WHO WE ARE (/about)

## 1. Overview & Context
- **Target Route**: `/about` (Who We Are)
- **App Type**: Existing NGO Cultural Website with Visual CMS
- **Design Archetype**: Minimal Editorial Webpage Mockup (Swiss & High-Contrast Editorial Monochrome)
- **Visual Source of Truth**: Minimal Editorial Webpage Mockup screenshot
- **Content Source of Truth**: Approved PDF Text from `WHO WE ARE (2).pdf`

---

## 2. Typography System
- **Heading Font**: `Cormorant, Georgia, serif`
- **Body Font**: `Public Sans, -apple-system, sans-serif`
- **Mono / Eyebrow Font**: `Public Sans, sans-serif` / `ui-monospace`

### Font Scale & Hierarchy
- **H1 (Hero Heading)**: `font-serif font-normal text-3xl sm:text-4xl lg:text-5xl tracking-tight leading-tight text-[#111111]`
- **H2 (Section Headings - THE CORE, OUR APPROACH)**: `font-serif font-normal text-2xl sm:text-3xl lg:text-4xl text-[#111111] uppercase tracking-wider`
- **Eyebrow / Overline**: `font-sans font-semibold text-xs tracking-[0.2em] text-[#111111] uppercase`
- **Body Text**: `font-sans font-light text-base sm:text-lg leading-relaxed text-[#444444]`
- **Placeholder Labels / Team Titles**: `font-sans font-medium text-sm tracking-wide text-[#666666]`

---

## 3. Color Palette & Surface Strategy
- **Background**: `#FFFFFF` (Pure white base)
- **Surface / Card Background**: `#F9F9F9` / `#F4F4F4`
- **Text Primary**: `#111111`
- **Text Body**: `#444444`
- **Text Muted**: `#666666`
- **Border**: `#E6E6E6` (Crisp 1px subtle strokes)
- **Hover State**: Subtle border darkening to `#111111` with smooth transition

---

## 4. Layout & Section Structure

### Section 1: Hero & Introduction
- **Container**: Max-width `1376px`, centered (`mx-auto px-6 sm:px-12 lg:px-16`)
- **Eyebrow**: "WHO WE ARE"
- **Main Heading**: "Urban Suburban Perspectives (USP) works at the intersection of heritage, art and culture."
- **Intro Prose (4 Paragraphs)**:
  1. "Urban Suburban Perspectives (USP) works at the intersection of heritage, art and culture. It grew from a shared appreciation of our cultural inheritance, a passion for creative expression, and a desire to translate these interests into meaningful, enduring work."
  2. "Our work takes different forms—from heritage conservation and traditional crafts to original theatre. Through these initiatives, we seek to preserve and renew cultural knowledge, nurture artistic expression, and create opportunities for learning, livelihood, and community engagement."
  3. "We believe that heritage, art and culture are not merely valuable in themselves; they can also bring people together, foster dialogue, strengthen communities, support local enterprise, and contribute to social, cultural and economic well-being."
  4. "Our aim is to develop work that honours the past while engaging with the present and remaining open to new ideas—creating meaningful experiences and lasting value for the people and communities with whom we work."

### Section 2: THE CORE (Team Grid)
- **Section Heading**: "THE CORE"
- **Placeholders**: 5 editable team portrait/name/introduction placeholders (`PhotoPlaceholder.jsx`)
- **Layout Grid**:
  - Desktop (>=1024px): 5-column grid or 3-top + 2-centered layout with `gap-8`
  - Tablet (768px - 1023px): 3-column + 2-column grid
  - Mobile (<768px): 1-column stack with generous vertical spacing (`gap-6`)
- **Card Style**: Crisp 1px `#E6E6E6` border, subtle background `#F9F9F9`, aspect ratio `4/5` or `1/1` for portrait placeholder, editable text block for name and intro.

### Section 3: OUR APPROACH & Principles
- **Section Heading**: "OUR APPROACH"
- **Approach Narrative (3 Paragraphs)**:
  1. "Every initiative begins with an understanding of the people, places, and traditions involved. This means exploring what already exists, recognising the knowledge and experiences people bring, and considering what new possibilities might emerge."
  2. "Bringing together different skills and perspectives creates opportunities for collaboration and experimentation, allowing ideas to develop through participation, practice, and exchange."
  3. "We believe there is room for both preservation and imagination. Historic buildings can find new purposes without losing their character, traditional skills can inspire contemporary design, and familiar stories can find new forms of expression."
- **Four Principles Grid**:
  - Grid: `grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6`
  - Cards:
    1. **Cultural Sustainability**
    2. **Conscious Practice**
    3. **Responsible Innovation**
    4. **Collaboration & Community**
  - Card Aesthetics: Clean 1px stroke border, white/subtle background, generous internal padding (`p-6` to `p-8`).

---

## 5. Responsive Breakpoints Strategy
- **320px (Mobile Small)**: Single column vertical stack, `px-4`, H1 `32px`, H2 `24px`
- **768px (Tablet)**: 2-column grid for team/principles, `px-8`, H1 `38px`, H2 `26px`
- **1024px (Laptop)**: Multi-column grid layout, `px-12`, H1 `44px`, H2 `28px`
- **1440px (Desktop)**: Optimal editorial spacing, `px-16`, H1 `48px`, H2 `32px`
- **1920px (Ultra-wide)**: Max-width container (`1376px`), H1 `52px`, H2 `34px`

---

## 6. Testing & Data Attributes
- All interactive and key elements MUST include `data-testid` attributes:
  - `data-testid="about-hero-heading"`
  - `data-testid="about-intro-prose"`
  - `data-testid="the-core-section-heading"`
  - `data-testid="the-core-team-grid"`
  - `data-testid="team-member-placeholder-1"` to `5`
  - `data-testid="our-approach-section-heading"`
  - `data-testid="our-approach-principles-grid"`
  - `data-testid="principle-card-cultural-sustainability"`
  - `data-testid="principle-card-conscious-practice"`
  - `data-testid="principle-card-responsible-innovation"`
  - `data-testid="principle-card-collaboration-community"`

---

## 7. Integration & CMS Preservation
- Maintain full compatibility with existing `Blocks.jsx`, `PhotoPlaceholder.jsx`, `LiveEditor.jsx`
- Preserve live edit capabilities and nested structure for page field edits.
