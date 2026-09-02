# UI credits

MotionButton in src/Studio.tsx is adapted from Animate UI's Button primitive:
https://animate-ui.com/docs/primitives/buttons/button
https://animate-ui.com/r/primitives-buttons-button.json

Copyright (c) 2025 Elliot Sutton. MIT + Commons Clause License Condition.
The full upstream license is preserved in ANIMATE_UI_LICENSE.md.
The optional Slot branch was removed and reduced-motion support added.

Anime.js powers the entrance sequence. The 3D resonance artwork uses original perspective-projection code on a canvas.
IBM Plex Mono is bundled locally through Fontsource. Manrope was removed in the font-polish pass.
Ciridae informed the editorial direction; its assets and branding are not copied.

## Supplied display font

Krylon is the sole display typeface, supplied by the user in krylon.zip.
The bundled readme states it is free for personal and commercial projects.
The original note and creator link are preserved in src/assets/fonts/krylon-readme.txt.
Brave Love and Hathem Bosteem are no longer used or distributed in this build.

## AI Elements transcription

The Transcription and TranscriptionSegment components are adapted from Vercel AI Elements:
https://github.com/vercel/ai-elements/blob/main/packages/elements/src/transcription.tsx
https://elements.ai-sdk.dev/components/transcription

Copyright 2023 Vercel, Inc. Apache-2.0. The upstream notice is preserved in
AI_ELEMENTS_LICENSE.txt and the full license in APACHE-2.0.txt.
Changes: local segment types instead of the AI SDK type import, controlled playback time,
plain CSS instead of Tailwind utilities, and non-interactive spans when seeking is absent.
Live sentence highlighting is driven by decoded audio duration and the AudioContext clock.
