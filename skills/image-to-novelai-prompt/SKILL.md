---
name: image-to-novelai-prompt
description: >-
  Analyze an attached reference image and turn its visible content into NovelAI
  prompts: a sectioned editable template plus a flat paste-ready tag string. Use
  when extracting, reverse-engineering, organizing, or reproducing an image as a
  prompt.
---
# Reference Image to NovelAI Prompt

Inspect the attached image itself before writing. Describe visible evidence and avoid presenting guessed character identities, franchises, or hidden generation settings as facts. If the user supplies a character identity, preserve it unless the image clearly conflicts.

## Why two outputs

NovelAI scores **comma-separated tags**, not Markdown structure. Section headings (`# Clothing`, etc.) are for **you** to edit conditions by hand; if they are pasted into the generator, they waste tokens and can dilute the tag signal. A flat string is usually closer to what the model was trained on. The skill therefore always emits **both**:

1. **Editable (templated)** — 11 sections for swapping pose, clothes, light, etc.
2. **Paste-ready (flat)** — the same tags concatenated in section order, **no headings**, ready to paste into NovelAI.

Do not replace tags with long prose paragraphs. “Non-templated” here means **flat dense tags**, not natural-language essays. Prefer short Danbooru-style phrases over sentence-like clauses unless a relationship truly needs a short clause (e.g. gaze between two figures).

## Editable output — exact sections, in order

1. `# General Quality`
2. `# Style String`
3. `# Character`
4. `# Clothing`
5. `# Action and Pose`
6. `# Expression and Gaze`
7. `# Environment`
8. `# Lighting`
9. `# Camera Angle and Composition`
10. `# Background`
11. `# Overall Style and Atmosphere`

Write comma-separated English tags under every heading. Keep each section composable as a prompt-template fragment. Use NovelAI emphasis such as `{tag}` or `{{tag}}` only for the few defining visual anchors. Do not wrap either output in a code fence unless the user asks.

Sections 1–2 are a fixed prefix the user keeps across every image (a default is given in [references/format-and-example.md](references/format-and-example.md); users are expected to replace it with their own). Reproduce the user's current prefix exactly. Do not rewrite, reorder, deduplicate, correct, or reinterpret it. Generate or replace only sections 3–11 unless the user explicitly asks to change the prefix.

## Paste-ready output

After the editable block, add a clear separator and a flat prompt:

```
---
## Paste-ready
```

Then one continuous comma-separated string: concatenate sections 1→11 in order, strip all `# …` headings and blank lines between sections, keep a single trailing comma style consistent with the templates, and remove near-duplicate phrases that only appeared because the same idea sat in two adjacent sections. Do not invent new tags in the flat version; it is the same content, densified for pasting.

If the user asks for **only** the template or **only** the flat string, emit that one. Default is both.

When the user asks for a small edit (“只改动作”), update the relevant section in the editable block **and** refresh the paste-ready string so they stay in sync.

## Anime priority

For anime imagery, use this priority order: **shape, dynamic tension, expression**. Composition, lighting, clothing, and atmosphere should reinforce those three rather than compete with them. Preserve unusual image-specific traits instead of replacing them with generic quality tags. Mention text, signatures, or watermarks only if the user explicitly wants them reproduced; otherwise omit them.

### Start with the three anime anchors

1. **Shape (`型`)**: recognizable silhouette, large hair masses, face shape, costume outline, proportion rhythm, dominant light-dark or color blocks. Large readable forms before small accessories.
2. **Dynamic tension (`动态张力`)**: line of action; directional relationships among head, ribcage, pelvis, limbs, hair, clothing, crop, and negative space. Quiet close-ups still need opposing tilts, unequal depth, compression, pull, or suspended motion.
3. **Expression (`表情塑造`)**: eyelid openness, brow tension, mouth state, gaze target, head direction, and any contradiction between them. Prefer a precise emotional state over `smile` / `beautiful face`.

Spend prompt detail in that order. If a minor clothing, background, quality, or mood tag does not strengthen shape, tension, expression, identity, or a user-required fact, omit it.

## Preserve visual plausibility

Stylization may simplify structure, perspective, and lighting, but it must not create obvious common-sense contradictions.

- Keep object depth and convergence readable. Avoid reverse perspective, impossible overlap, or objects widening in the wrong depth direction unless deliberate in the reference.
- Keep hands and finger structure coherent when hands are in frame.
- Treat light as designed: clear light-shadow separation, transmitted light through sheer material, bounce light—while keeping the dominant light direction consistent across face, body, clothing, and casts.

## Design hierarchy, depth, and visual guidance

Translate the reference into a composition with an intentional reading order.

- Identify a trend line through pose, gaze, hair, clothing, props, architecture, light, or background shapes. Describe enclosures as in-scene structures (doorway, window, arch, shadow mass)—not as a graphic border or page frame.
- Preserve unequal information density and scale; asymmetrical clusters and negative space.
- Keep important facial features comparatively complex and specific.
- Make foreground, subject plane, and background distinguishable through scale, overlap, value, and depth of field.
- Direct hair, collar, folds, accessories, and light toward or around the face unless another focal point is requested.
- Prefer limited value steps and clean color-block boundaries for anime readability.

## Preserve distinctive visual choices

- Preserve unusual image-specific choices.
- Make pose and camera less generic when the reference supports it, without breaking anatomy or identity.
- Build fashion through controlled unfamiliarity when appropriate.
- Give the frame a concrete unanswered question grounded in visible action, expression, gaze, or environment—do not fabricate canon.

## Build a story frame, not a character inventory

When multiple figures appear, track head/ribcage/pelvis orientation, gaze relationships, asymmetry, occlusion, and relative depth. Prefer a restrained narrative beat over generic scene labels. Do not invent plot unsupported by image or user direction.

## Keep every tag useful

Use the shortest prompt that preserves defining information.

- One clear phrase per visual idea; remove exact duplicates and near-synonym stacks.
- Omit anatomy tags for parts outside the frame.
- Prefer observable features over vague praise (`beautiful`, `detailed`, `cinematic` spam).
- Keep `# General Quality` compact.
- Before answering, reread across section boundaries and remove repetition; the paste-ready string must not reintroduce what you just cleaned.

## Avoid unintended frames

Unless the user wants a poster/page/card/manga panel/visible border, describe camera framing directly and avoid `border`, `frame`, `poster layout`, `cover design`, `manga panel`, etc. Treat `editorial` / `character poster` as potentially frame-inducing.

## Thumbnail-friendly composition (default for social posts)

Images for feeds such as Xiaohongshu or Instagram are judged as small thumbnails first. Unless the user asks for something else, default to:

- **A large face that still reads as a thumbnail**: `{{upper body}}` or `close-up`; avoid `full body` / `wide shot` unless requested (add them to the negative prompt).
- **Eye contact**: `looking at viewer`, so the image feels one-on-one.
- **One subtle emotion**: a single precise state (shy, gentle, teasing, wistful), not a stack of expressions.
- **One memorable scene detail**: something a viewer could sum up in one sentence (a heart drawn on a foggy window, a pressed flower between book pages).
- **Two-color palette**: one environment color plus the character's hair color, e.g. `misty blue and pink palette`.
- **Simplified background**: `blurred background, bokeh, simple background`.
- **Asymmetric framing**: offset the figure, tilt props or hands, use side light. Avoid perfectly centered, symmetrical compositions, which tend to look stiff.

Useful negative additions for this style: `full body, wide shot, small face, cluttered background, multiple girls, text, logo`.

## Generating with the local backend

When the NovelAI Local Backend in this repository is running (default `http://127.0.0.1:8787`):

1. Write the paste-ready prompt, then call `POST /generate` with `prompt`, `negative_prompt` (omit to use the backend default), `n` (2 is a good default so the user can choose), and a short `label` such as `01_foggy_window`.
2. Show the user small previews (about 720 px tall) together with each filename and the full prompt. Treat the user as the final judge of taste.
3. On feedback, edit the relevant section, refresh the paste-ready string, and regenerate. Add specific negatives for recurring mistakes (for example `tears, crying` when a tear-wiping pose puts tears on the wrong face).
4. When the user picks one, call `POST /upscale` with its filename and deliver the upscaled PNG.
5. On HTTP 429, do not retry automatically; give the user the prompt and try again later.

For the canonical formatting and a worked example of **both** outputs, read [references/format-and-example.md](references/format-and-example.md).
