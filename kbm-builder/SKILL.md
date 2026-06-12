---
name: kbm-builder
description: "Use this skill whenever someone asks to create a KBM, Knowledge Base Manual, or bot knowledge doc for LimeChat. Triggers: 'create KBM', 'make KBM', 'build knowledge base', 'KBM for [brand]', or any mention of creating a doc for the LimeChat bot builder. When this skill is loaded, immediately ask the user for the brand website and FAQ/policy URLs before doing anything else."
---

# LimeChat KBM (Knowledge Base Manual) — Skill File

---

## FIRST THING TO DO WHEN THIS SKILL IS LOADED

**Do NOT start building anything yet.**

Ask the user this exact question first:

```
Great! To build the KBM I'll need the brand's website and any 
FAQ or policy page links.

Please share:
1. Brand website URL (e.g. https://brandname.com)
2. Any FAQ, policy, or help page URLs — paste as many as you have
   (e.g. FAQ page, shipping policy, return policy, contact page)

You can paste 1 link or 10 — share whatever you have and 
I'll fetch them all and build the full KBM.
```

**Wait for the URLs. Do not proceed until at least 1 URL is received.**

---

## STEP 1 — DATA COLLECTION (after URLs received)

Once the user shares URLs, fetch ALL of them using `web_fetch`.

**Always fetch these pages automatically** even if not shared:
```
[website]/pages/faq
[website]/pages/contact
[website]/pages/shipping
[website]/pages/shipping-policy
[website]/pages/returns
[website]/pages/refund-policy
[website]/pages/refund-and-cancellation
[website]/pages/terms-and-conditions
[website]/pages/privacy-policy
[website]/pages/track-order
[website]/pages/tracking
[website]/about
[website]/pages/about-us
```

If a page returns an error or is empty — skip it and move on.

**Extract and note the following from all pages:**

| Data Point | Where to find it |
|---|---|
| Brand name, tagline, parent company | Homepage |
| Product categories | Homepage nav + collections |
| Bestsellers + prices | Homepage or /collections/bestsellers |
| Active promo codes / offers | Homepage banners, announcement bar |
| Free shipping threshold | Shipping policy or homepage |
| Return policy + window (days) | Returns / refund page |
| Damage reporting window (days) | Returns page |
| Cancellation policy | Returns or terms page |
| Refund timeline (business days) | Returns page |
| Support phone + hours | Contact page |
| WhatsApp number | Contact page or footer |
| Support email | Contact page or footer |
| Order tracking URL | Footer or contact page |
| Social media handles | Footer |

**Do not build the KBM until all available data is collected.**

---

## STEP 2 — SECTION MAPPING

Map scraped data to KBM sections. Always include:

```
SECTION 1  — About [Brand]
SECTION 2  — Product Range & Categories
SECTION 3  — Bestsellers / Key Products
SECTION 4  — Offers & Pricing
SECTION 5  — Orders
SECTION 6  — Shipping & Delivery
SECTION 7  — Returns, Refunds & Cancellations
SECTION 8  — My Account
SECTION 9  — Have Any Queries (policy links)
SECTION 10 — Contact Us
```

Add extra sections based on what the brand has:
- Subscriptions → if brand has subscription plan
- Wholesale / B2B → if brand has B2B page
- Product Knowledge → if brand has brewing guides, usage guides, etc.
- Authenticity / Testing → if brand has certification or testing programs
- Kids / Specific Range → if brand has a sub-range worth its own section

---

## STEP 3 — BUILD THE DOCX

Use Node.js with the `docx` npm package. Template below.

---

### ⚠️ CRITICAL KEEPNEXT RULES — READ BEFORE WRITING ANY CODE

These rules were validated through real KBM production. Violating them causes blank pages, floating lines, and Q&A splits.

| Rule | Detail |
|---|---|
| `keepNext: true` ONLY on `qPara()` and `ansLabel()` | Glues Q lines to the Answer label. That is ALL. |
| NEVER put `keepNext: true` on `para()` | Causes a chain so long Word pushes entire Section 1 to page 2, leaving page 1 blank |
| NEVER put `keepNext: true` on `bullet()` | Same issue — extends the chain uncontrollably |
| NEVER put `keepNext: true` in the bullet numbering style | Overrides paragraph-level settings and creates invisible chain |
| `keepLines: true` on ALL paragraphs | Prevents a single paragraph from splitting mid-line. This is safe on everything. |
| `pageBreakBefore: false` on ALL headings | Must be set in BOTH the paragraph AND the style definition |
| `keepNext: true` on heading style definition | Must be in BOTH the paragraph AND the style definition |
| Title subtitle line must have `keepNext: false` explicitly | Without it the subtitle chains into Section 1 heading, pushing all content off page 1 |
| Do NOT use `divider()` calls in the document body | Dividers float to top of pages as orphan lines. Use paragraph spacing for separation instead. |
| NEVER place `blank()` before `divider()` if using dividers | The blank breaks the keepNext chain and lets the divider drift to the next page alone |

---

### Helper Functions (always use these exactly as written)

```javascript
const {
  Document, Packer, Paragraph, TextRun, AlignmentType,
  HeadingLevel, LevelFormat, BorderStyle
} = require('docx');
const fs = require('fs');

// keepNext: true — chains to next paragraph (Q to Q to Answer label)
function qPara(label, text) {
  return new Paragraph({
    spacing: { before: 80, after: 40 },
    keepNext: true, keepLines: true,
    children: [
      new TextRun({ text: label + ' ', bold: true, font: 'Arial', size: 22 }),
      new TextRun({ text, bold: true, italics: true, font: 'Arial', size: 22 }),
    ]
  });
}

// keepNext: true — chains Answer label to first answer line
function ansLabel() {
  return new Paragraph({
    spacing: { before: 40, after: 40 },
    keepNext: true, keepLines: true,
    children: [new TextRun({ text: 'Answer:', bold: true, font: 'Arial', size: 22 })]
  });
}

// NO keepNext — answer content never chains. keepLines only.
function para(text, { bold = false, italic = false, before = 40, after = 40 } = {}) {
  return new Paragraph({
    spacing: { before, after }, keepLines: true,
    children: [new TextRun({ text, bold, italics: italic, font: 'Arial', size: 22 })]
  });
}

// keepNext: true on heading — must also be in style def (see Document Setup)
function sectionHeading(text, color = '1A5276') {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 160 },
    keepNext: true, keepLines: true,
    pageBreakBefore: false,
    children: [new TextRun({ text, bold: true, font: 'Arial', size: 28, color })]
  });
}

function subHeading(text, color = '2E75B6') {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 200, after: 100 },
    keepNext: true, keepLines: true,
    pageBreakBefore: false,
    children: [new TextRun({ text, bold: true, font: 'Arial', size: 24, color })]
  });
}

// NO keepNext on bullets — keepLines only
function bullet(text) {
  return new Paragraph({
    numbering: { reference: 'bullets', level: 0 },
    spacing: { before: 40, after: 40 }, keepLines: true,
    children: [new TextRun({ text, font: 'Arial', size: 22 })]
  });
}

function blank() {
  return new Paragraph({ spacing: { before: 20, after: 20 }, children: [new TextRun('')] });
}
```

> **Note:** `divider()` function is intentionally omitted. Do not add horizontal rule lines — they orphan at the top of pages. Use paragraph spacing for visual separation.

---

### Document Setup (always use this)

```javascript
const doc = new Document({
  numbering: {
    config: [{
      reference: 'bullets',
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: '\u2022',
        alignment: AlignmentType.LEFT,
        // NO keepNext in numbering style — it overrides paragraph-level settings
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    }]
  },
  styles: {
    default: { document: { run: { font: 'Arial', size: 22 } } },
    paragraphStyles: [
      {
        id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: 'Arial', color: 'H1_COLOR' },
        // keepNext + keepLines + pageBreakBefore: false MUST be here in style def AND in sectionHeading()
        paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0, pageBreakBefore: false, keepNext: true, keepLines: true }
      },
      {
        id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: 'Arial', color: 'H2_COLOR' },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1, pageBreakBefore: false, keepNext: true, keepLines: true }
      }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
      }
    },
    children: [ /* all paragraphs go here */ ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('/home/claude/[Brand]_KBM_v1.docx', buffer);
  console.log('Done');
});
```

---

### Title Block Pattern

```javascript
// Title — no keepNext needed
new Paragraph({
  spacing: { before: 0, after: 200 },
  keepLines: true,
  children: [new TextRun({ text: '[Brand] — Knowledge Base Manual', bold: true, font: 'Arial', size: 36, color: H1 })]
}),
// CRITICAL: subtitle must have keepNext: false explicitly — otherwise it chains into Section 1
// and Word pushes the entire first section off page 1, leaving page 1 blank
para('Bot Knowledge Reference Document', { italic: true, before: 0, after: 40 }),
// No divider here — just let section heading spacing handle the gap
```

---

### Q&A Block Pattern

```javascript
// Questions: keepNext chains Q1 → Q2 → Q3 → ansLabel
qPara('Q1:', 'Primary question phrasing?'),
qPara('Q2:', 'Alternative phrasing?'),
qPara('Q3:', 'Another variant?'),
// ansLabel: keepNext chains to first answer line
ansLabel(),
// Answer content: NO keepNext — just keepLines. Can span pages if needed.
para('Answer text here.'),
bullet('Bullet point if list answer'),
bullet('Another bullet'),
// blank() for spacing between Q&A blocks — no divider()
blank(),
```

---

## STEP 4 — VALIDATION CHECKLIST

Run through this before calling `present_files`. Fix any issues found.

### Pre-output checks

```
[ ] Page 1 is NOT blank
      → If blank: subtitle line after title is missing keepNext: false
      → Or: a para()/bullet() somewhere has keepNext: true creating a chain too long for page 1

[ ] No orphan divider lines at top of any page
      → Fix: remove all divider() calls — use blank() + paragraph spacing instead

[ ] Section headings stay with their first Q line (not left alone at bottom of page)
      → Fix: keepNext: true must be in BOTH sectionHeading() paragraph AND Heading1 style def

[ ] Q lines and Answer: label are never separated from each other
      → Fix: keepNext: true on all qPara() and ansLabel()

[ ] Answer content (para, bullets) may flow across pages — this is acceptable
      → keepLines: true prevents a single para from splitting mid-sentence

[ ] No syntax errors — especially apostrophes in bullet() strings
      → Use straight apostrophes in JS strings, e.g. "brand's" not "brand's"

[ ] Output file is non-zero size
      → Run: ls -lh /home/claude/[Brand]_KBM_v1.docx
```

### Run order

```bash
node [brand]_kbm.js                          # build
# check output says "Done"
cp /home/claude/[Brand]_KBM_v1.docx /mnt/user-data/outputs/[Brand]_KBM_v1.docx
# then present_files
```

---

## Brand Colour Reference

| Brand | H1 Colour | H2 Colour |
|---|---|---|
| Novology | 1F4E79 | 2E75B6 |
| HyugaLife | 1A5276 | 1F618D |
| PlixLife | 1E6B2E | 2E8B57 |
| Blue Tokai | 1B4F8A | 2471A3 |
| VERO MODA | 1C1C1C | 4A4A4A |

For new brands — pick a colour that matches the brand's primary colour.

---

## Completed KBMs Log

| Brand | File | Sections | Notes |
|---|---|---|---|
| Novology | Novology_KBM_v1.docx | 9 | Skincare, Unilever, TT-2/HNR3 |
| HyugaLife | HyugaLife_KBM_v1.docx | 9 | Supplements, H-Tested, 15-day return |
| PlixLife | PlixLife_KBM_v1.docx | 9 | Plant-based, Clean Label, 30-day return |
| Blue Tokai | BlueTokai_KBM_v1.docx | 13 | Specialty coffee, TRY10, subscriptions |
| VERO MODA | VeroModa_KBM_v1.docx | 12 | Women's fashion, BESTSELLER, GST 2.0, Curve/Marquee/Girl |

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `keepNext: true` on `para()` | Page 1 is blank — all content pushed to page 2 | Remove keepNext from para(). Only qPara + ansLabel get keepNext. |
| `keepNext: true` on `bullet()` | Page 1 blank or large gaps between sections | Remove keepNext from bullet(). keepLines only. |
| `keepNext: true` in numbering style | Bullets ignore paragraph-level keepNext, chain uncontrollably | Remove keepNext from numbering config style block |
| Subtitle line after title has no `keepNext: false` | Page 1 blank | para('subtitle', { keepNext: false }) — must be explicit |
| `divider()` in document | Orphan horizontal line floating at top of pages | Remove all divider() calls. Use blank() + spacing. |
| `blank()` before `divider()` | Divider drifts to next page alone | If using dividers: place divider() directly, no blank() before it |
| `pageBreakBefore` only in paragraph, not style def | Section heading left alone at bottom of page | Set pageBreakBefore: false in BOTH paragraph AND paragraphStyles |
| `keepNext` only in paragraph, not style def | Heading separated from first Q line | Set keepNext: true in BOTH paragraph AND paragraphStyles |
| Apostrophes in bullet strings | Script syntax error | Use straight apostrophes in JS strings |
| Script runs but file is 0 bytes | Packer silent fail | Wrap Packer.toBuffer in try/catch, log errors |

---

## File Naming Convention

```
[BrandName]_KBM_v[version].docx

Novology_KBM_v1.docx
HyugaLife_KBM_v1.docx
PlixLife_KBM_v1.docx
BlueTokai_KBM_v1.docx
VeroModa_KBM_v1.docx
```

Increment version on every update.
