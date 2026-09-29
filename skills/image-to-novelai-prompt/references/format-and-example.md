# Output format and worked example

Emit **two** blocks by default:

1. **Editable (templated)** — Markdown headings + comma-separated English tags, one blank line between sections. For hand-editing conditions.
2. **Paste-ready (flat)** — same tags concatenated 1→11 with **no** headings, for pasting into NovelAI.

Do not add explanations before or after unless uncertainty materially affects the result. Prefer dense Danbooru-style tags over prose sentences. The example is intentionally economical: each phrase should add a distinct visual instruction.

The first two sections are the user's fixed prefix. The version below is a neutral default with no artist names; replace it with your own. Once set, reproduce it exactly, including spelling, weights, punctuation, and escaping, unless the user explicitly asks to edit it:

# General Quality

masterpiece, best quality, amazing quality, very aesthetic, absurdres, highly detailed, newest, anime illustration, natural proportions, anatomically correct hands, well-drawn hands,

# Style String

delicate lineart, clean cel shading, soft painterly coloring, luxury fashion editorial, glamorous celebrity photography,

Generate sections 3-11 from the reference. The worked example below shows those variable sections, then the flat paste-ready string.

The following example is derived from a vertical anime illustration of a pink-haired fantasy woman framed by white feather-like forms against a black background.

## Editable

# Character

1girl, solo, mature woman, {{short pink layered bob}}, side bangs covering one eye, pointed ears, pale skin, feather hair ornament, dangling black earrings,

# Clothing

{{black strapless fitted gown}}, sweetheart neckline, white feather motifs, pink accents, pearl chains across the bodice and waist, black choker, asymmetric ceremonial dress,

# Action and Pose

{{standing in a three-quarter pose}}, ribcage leaning backward, head tilted upward in the opposite direction, diagonal shoulder line, one arm lowered behind the body,

# Expression and Gaze

half-lidded visible eye, looking away from the viewer, closed mouth, restrained melancholy,

# Environment

abstract dark fantasy space, {{enormous white feather-like forms curling around the body}}, dark bird silhouettes above,

# Lighting

high-contrast lighting, luminous skin, deep black shadows, cool blue reflected light,

# Camera Angle and Composition

{{vertical full-body composition}}, slightly low angle, character above center, white foreground forms rising from below, asymmetrical diagonal arrangement, narrow black background continuing to the image edges,

# Background

near-black background continuing to every edge, blue-black foliage, subtle grain, sparse negative space,

# Overall Style and Atmosphere

black, white, pale blue and vivid pink palette, gothic ceremonial mood, sacred yet ominous,

---

## Paste-ready

masterpiece, best quality, amazing quality, very aesthetic, absurdres, highly detailed, newest, anime illustration, natural proportions, anatomically correct hands, well-drawn hands, delicate lineart, clean cel shading, soft painterly coloring, luxury fashion editorial, glamorous celebrity photography, 1girl, solo, mature woman, {{short pink layered bob}}, side bangs covering one eye, pointed ears, pale skin, feather hair ornament, dangling black earrings, {{black strapless fitted gown}}, sweetheart neckline, white feather motifs, pink accents, pearl chains across the bodice and waist, black choker, asymmetric ceremonial dress, {{standing in a three-quarter pose}}, ribcage leaning backward, head tilted upward in the opposite direction, diagonal shoulder line, one arm lowered behind the body, half-lidded visible eye, looking away from the viewer, closed mouth, restrained melancholy, abstract dark fantasy space, {{enormous white feather-like forms curling around the body}}, dark bird silhouettes above, high-contrast lighting, luminous skin, deep black shadows, cool blue reflected light, {{vertical full-body composition}}, slightly low angle, character above center, white foreground forms rising from below, asymmetrical diagonal arrangement, narrow black background continuing to the image edges, near-black background continuing to every edge, blue-black foliage, subtle grain, sparse negative space, black, white, pale blue and vivid pink palette, gothic ceremonial mood, sacred yet ominous,
