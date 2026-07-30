"""Create the complete 11-object x 3-theme V6 grayscale review sheet."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/images/AnalogInstrumentMR_V6_11Objects_3Themes_Grayscale.png"
THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
THEME_LABELS = {
    "OrbitalAnalog": "ORBITAL\nANALOG",
    "ForgeBrass": "FORGE\nBRASS",
    "KineticSafety": "KINETIC\nSAFETY",
}
OBJECTS = (
    "MeterRound",
    "Lever",
    "Toggle",
    "Rotary",
    "Button",
    "Lamp",
    "Throttle",
    "PowerSlider",
    "StatusIndicator",
    "WindowMeter",
    "WindowPanel",
)
OBJECT_LABELS = {
    "MeterRound": "ROUND METER",
    "Lever": "LEVER",
    "Toggle": "TOGGLE",
    "Rotary": "ROTARY",
    "Button": "BUTTON",
    "Lamp": "LAMP",
    "Throttle": "THROTTLE",
    "PowerSlider": "POWER SLIDER",
    "StatusIndicator": "STATUS",
    "WindowMeter": "WINDOW METER",
    "WindowPanel": "WINDOW PANEL",
}
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def source_path(theme, key):
    return (
        ROOT
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"Preview_{key}_{theme}_V6_Grayscale.png"
    )


def main():
    canvas_width, canvas_height = 4260, 1440
    left, top = 250, 240
    cell_width, cell_height = 360, 360
    preview_size = 330
    image = Image.new("RGB", (canvas_width, canvas_height), (10, 15, 21))
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(FONT_BOLD, 50)
    subtitle = ImageFont.truetype(FONT, 24)
    header = ImageFont.truetype(FONT_BOLD, 20)
    theme_font = ImageFont.truetype(FONT_BOLD, 27)

    draw.text(
        (48, 34),
        "AnalogInstrumentMR V6 — 11 Objects × 3 Theme Families",
        font=title,
        fill=(237, 243, 248),
    )
    draw.text(
        (50, 105),
        "Hard-surface review: theme identity, mechanical support, and readable motion axes.",
        font=subtitle,
        fill=(147, 165, 179),
    )
    draw.text(
        (50, 143),
        "V6 rules: fitted joints, gaskets, bushings, limit stops, supported scales, and no floating parts.",
        font=subtitle,
        fill=(147, 165, 179),
    )

    for column, key in enumerate(OBJECTS):
        center_x = left + column * cell_width + cell_width / 2
        label = OBJECT_LABELS[key]
        box = draw.textbbox((0, 0), label, font=header)
        draw.text(
            (center_x - (box[2] - box[0]) / 2, top - 45),
            label,
            font=header,
            fill=(202, 215, 225),
        )

    for row, theme in enumerate(THEMES):
        y = top + row * cell_height
        draw.multiline_text(
            (35, y + 124),
            THEME_LABELS[theme],
            font=theme_font,
            fill=(183, 199, 211),
            spacing=8,
            align="center",
        )
        for column, key in enumerate(OBJECTS):
            x = left + column * cell_width
            source = Image.open(source_path(theme, key)).convert("RGB")
            source = source.resize(
                (preview_size, preview_size),
                Image.Resampling.LANCZOS,
            )
            paste_x = x + (cell_width - preview_size) // 2
            paste_y = y + 10
            image.paste(source, (paste_x, paste_y))
            draw.rounded_rectangle(
                (
                    paste_x - 1,
                    paste_y - 1,
                    paste_x + preview_size + 1,
                    paste_y + preview_size + 1,
                ),
                radius=9,
                outline=(52, 68, 81),
                width=2,
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, "PNG", optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
