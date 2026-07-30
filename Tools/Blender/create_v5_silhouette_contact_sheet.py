"""Create the 3 x 3 V5 grayscale silhouette review sheet."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = (
    ROOT
    / "docs/images/AnalogInstrumentMR_V5_ThemeSilhouette_3x3.png"
)
THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
THEME_LABELS = {
    "OrbitalAnalog": "ORBITAL ANALOG",
    "ForgeBrass": "FORGE BRASS",
    "KineticSafety": "KINETIC SAFETY",
}
OBJECTS = ("MeterRound", "Lever", "WindowPanel")
OBJECT_LABELS = {
    "MeterRound": "ROUND METER",
    "Lever": "CONTROL LEVER",
    "WindowPanel": "WINDOW PANEL",
}
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def source_path(theme, key):
    return (
        ROOT
        / "ArtSource/Blender/ThemeSilhouetteV5"
        / theme
        / f"Preview_{key}_{theme}_V5_Grayscale.png"
    )


def main():
    width, height = 2520, 2520
    left, top = 255, 230
    cell = 735
    image = Image.new("RGB", (width, height), (11, 16, 22))
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(FONT_BOLD, 48)
    subtitle = ImageFont.truetype(FONT, 23)
    header = ImageFont.truetype(FONT_BOLD, 27)
    small = ImageFont.truetype(FONT_BOLD, 18)

    draw.text(
        (48, 36),
        "AnalogInstrumentMR V5 — Grayscale Theme Silhouette Review",
        font=title,
        fill=(235, 242, 248),
    )
    draw.text(
        (50, 105),
        "Shared: envelope / mount / pivot only. "
        "Visible geometry is theme-specific.",
        font=subtitle,
        fill=(135, 153, 168),
    )
    draw.text(
        (50, 140),
        "Inset: the same preview reduced to 80 px, then enlarged.",
        font=subtitle,
        fill=(135, 153, 168),
    )

    for column, key in enumerate(OBJECTS):
        x = left + column * cell + cell / 2
        box = draw.textbbox(
            (0, 0),
            OBJECT_LABELS[key],
            font=header,
        )
        draw.text(
            (x - (box[2] - box[0]) / 2, top - 52),
            OBJECT_LABELS[key],
            font=header,
            fill=(199, 213, 224),
        )

    for row, theme in enumerate(THEMES):
        y = top + row * cell
        label = THEME_LABELS[theme].replace(" ", "\n")
        draw.multiline_text(
            (40, y + 275),
            label,
            font=header,
            fill=(177, 195, 208),
            spacing=8,
            align="center",
        )
        for column, key in enumerate(OBJECTS):
            x = left + column * cell
            source = Image.open(source_path(theme, key)).convert("RGB")
            source = source.resize((660, 660), Image.Resampling.LANCZOS)
            image.paste(source, (x + 20, y + 10))
            draw.rounded_rectangle(
                (x + 19, y + 9, x + 681, y + 671),
                radius=12,
                outline=(55, 70, 82),
                width=3,
            )
            tiny = source.resize((80, 80), Image.Resampling.LANCZOS)
            tiny = tiny.resize((160, 160), Image.Resampling.NEAREST)
            inset_x = x + 500
            inset_y = y + 486
            image.paste(tiny, (inset_x, inset_y))
            draw.rectangle(
                (inset_x - 2, inset_y - 2, inset_x + 162, inset_y + 162),
                outline=(210, 220, 228),
                width=2,
            )
            draw.text(
                (inset_x + 8, inset_y - 27),
                "80 px",
                font=small,
                fill=(218, 227, 234),
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, "PNG", optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
