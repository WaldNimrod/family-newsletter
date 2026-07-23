# Media Kit — Family Newsletter ("בית ולד 📰")

**Upload EVERY file in this folder into the context of your media-generation project
(Nano Banana / GPT / Claude project) BEFORE generating.** This locks ONE consistent
character and visual style across every asset and every session — that is the whole
point (continuity + unified style).

## Setup — two kinds of files
- **INSTRUCTIONS.md → paste into the project's "Instructions" / system-prompt field**
  (the operating directive: how the AI must behave). This is the piece most projects
  need separately from the knowledge files.
- The other three → **upload as knowledge / context files**:
  - **STYLE_BIBLE.md** — the locked visual system + the "Skipper Cat" mascot. Single
    source of truth for style / palette / character.
  - **PROMPTS.md** — per-asset generation prompts (compact — they rely on the bible in
    context) + exact output sizes, formats, and file paths.
  - **FAMILY_CHARACTERS.md** — the 5 family-member character designs (per-member art +
    continuity).

## Workflow (for maximum consistency)
1. Load all 3 files into the project context.
2. Generate the **Skipper Cat reference** (PROMPTS #1, `hero-greeting`) FIRST. Iterate
   until you love it.
3. **Add that image back into the project context** as the visual anchor.
4. Generate the rest — each new asset now matches both the written bible AND the
   reference image → the same cat every time.
5. Deliver exactly as PROMPTS.md specifies (filenames / paths / transparent PNG), then
   commit to origin so the build + runtime pick them up.

## Deeper reference (optional, richer source)
`archive/design-april-2026/DESIGN_FISH_2026-07-22.md` and `SVG_MODULE_SPEC.md` in the
repo — the original design analysis this kit distills. Upload them too if your tool
handles long context well.
