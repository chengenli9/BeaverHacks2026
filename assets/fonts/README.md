# Render Fonts

The renderer must use a repo-controlled font path for FFmpeg `drawtext` instead of relying on system fonts.

Required MVP font:

```text
assets/fonts/Inter-Bold.ttf
```

Inter is licensed under the SIL Open Font License. Keep the font file in this folder and copy it into each local project at:

```text
project/assets/fonts/Inter-Bold.ttf
```

Renderer validation should fail before FFmpeg starts if the manifest references a missing font file.

