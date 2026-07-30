"""Create the representative 3-theme x 3-object V6 review sheet."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/images/AnalogInstrumentMR_V6_HardSurface_3x3.png"
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
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"Preview_{key}_{theme}_V6_Grayscale.png"
    )


def main():
    width, height = 2520, 2520
    left, top = 255, 230
    cell = 735
    image = Image.new("RGB", (width, height), (10, 15, 21))
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(FONT_BOLD, 48)
    subtitle = ImageFont.truetype(FONT, 23)
    header = ImageFont.truetype(FONT_BOLD, 27)

    draw.text(
        (48, 36),
        "AnalogInstrumentMR V6 — Hybrid Hard-Surface Review",
        font=title,
        fill=(235, 242, 248),
    )
    draw.text(
        (50, 105),
        "V4 topology density + V5 theme silhouettes and mechanical supports.",
        font=subtitle,
        fill=(141, 160, 174),
    )
    draw.text(
        (50, 140),
        "Geometry: silhouette / layers / bearings / guards. "
        "Maps: engraving / micro grooves / wear / labels.",
        font=subtitle,
        fill=(141, 160, 174),
    )

    for column, key in enumerate(OBJECTS):
        center_x = left + column * cell + cell / 2
        label = OBJECT_LABELS[key]
        box = draw.textbbox((0, 0), label, font=header)
        draw.text(
            (center_x - (box[2] - box[0]) / 2, top - 52),
            label,
            font=header,
            fill=(202, 215, 225),
        )

    for row, theme in enumerate(THEMES):
        y = top + row * cell
        draw.multiline_text(
            (36, y + 275),
            THEME_LABELS[theme].replace(" ", "\n"),
            font=header,
            fill=(181, 198, 211),
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

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, "PNG", optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
