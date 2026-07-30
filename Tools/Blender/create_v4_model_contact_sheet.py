"""Create the deterministic 11-object x 3-theme V4 review contact sheet."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = (
    ROOT
    / "docs/images/AnalogInstrumentMR_V4_11Objects_3Themes_ContactSheet.png"
)

OBJECTS = (
    ("MeterRound", "METER"),
    ("Lever", "LEVER"),
    ("Toggle", "TOGGLE"),
    ("Rotary", "ROTARY"),
    ("Button", "BUTTON"),
    ("Lamp", "LAMP"),
    ("Throttle", "THROTTLE"),
    ("PowerSlider", "POWER\nSLIDER"),
    ("StatusIndicator", "STATUS\nLED"),
    ("WindowMeter", "WINDOW\nMETER"),
    ("WindowPanel", "WINDOW\nPANEL"),
)

THEMES = (
    ("KineticSafety", "KINETIC\nSAFETY", (68, 195, 229)),
    ("ForgeBrass", "FORGE\nBRASS", (221, 154, 65)),
    ("OrbitalAnalog", "ORBITAL\nANALOG", (82, 177, 235)),
)

FONT_REGULAR = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

CANVAS_WIDTH = 4096
CANVAS_HEIGHT = 1380
LEFT = 250
TOP = 175
CELL_WIDTH = 344
CELL_HEIGHT = 365
THUMB_SIZE = 318


def preview_path(theme, key):
    if theme == "KineticSafety" and key == "Lever":
        return (
            ROOT
            / "ArtSource/Blender/HardSurfacePrototype/KineticSafety/"
            "Preview_Lever_KineticSafety_HS_V3_Retopo.png"
        )
    return (
        ROOT
        / "ArtSource/Blender/HardSurfacePrototype"
        / theme
        / "V4"
        / f"Preview_{key}_{theme}_HS_V4.png"
    )


def fit_text(draw, text, center, font, fill, spacing=2):
    box = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        anchor="la",
        spacing=spacing,
        align="center",
    )
    width = box[2] - box[0]
    height = box[3] - box[1]
    draw.multiline_text(
        (center[0] - width / 2, center[1] - height / 2),
        text,
        font=font,
        fill=fill,
        spacing=spacing,
        align="center",
    )


def main():
    missing = [
        str(preview_path(theme, key))
        for theme, _, _ in THEMES
        for key, _ in OBJECTS
        if not preview_path(theme, key).is_file()
    ]
    if missing:
        raise FileNotFoundError("\n".join(missing))

    canvas = Image.new(
        "RGB",
        (CANVAS_WIDTH, CANVAS_HEIGHT),
        (12, 17, 23),
    )
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.truetype(FONT_REGULAR, 48)
    subtitle_font = ImageFont.truetype(FONT_REGULAR, 23)
    object_font = ImageFont.truetype(FONT_BOLD, 21)
    theme_font = ImageFont.truetype(FONT_BOLD, 25)
    footer_font = ImageFont.truetype(FONT_REGULAR, 19)

    draw.text(
        (48, 34),
        "AnalogInstrumentMR — 3Dモデル V4 クオリティレビュー",
        font=title_font,
        fill=(235, 244, 251),
    )
    draw.text(
        (50, 98),
        "11 objects × 3 themes | Quality floor: "
        "Lever_KineticSafety_HS_V3_Retopo",
        font=subtitle_font,
        fill=(139, 160, 176),
    )

    for column, (_, label) in enumerate(OBJECTS):
        x = LEFT + column * CELL_WIDTH
        fit_text(
            draw,
            label,
            (x + CELL_WIDTH / 2, TOP - 46),
            object_font,
            (196, 211, 222),
        )

    for row, (theme, label, accent) in enumerate(THEMES):
        y = TOP + row * CELL_HEIGHT
        draw.rounded_rectangle(
            (28, y + 16, LEFT - 24, y + THUMB_SIZE - 16),
            radius=22,
            fill=(20, 28, 36),
            outline=accent,
            width=3,
        )
        fit_text(
            draw,
            label,
            ((LEFT - 8) / 2, y + THUMB_SIZE / 2),
            theme_font,
            accent,
            spacing=7,
        )

        for column, (key, _) in enumerate(OBJECTS):
            x = LEFT + column * CELL_WIDTH
            source = Image.open(preview_path(theme, key)).convert("RGB")
            source.thumbnail(
                (THUMB_SIZE, THUMB_SIZE),
                Image.Resampling.LANCZOS,
            )
            tile = Image.new(
                "RGB",
                (THUMB_SIZE, THUMB_SIZE),
                (22, 28, 34),
            )
            offset = (
                (THUMB_SIZE - source.width) // 2,
                (THUMB_SIZE - source.height) // 2,
            )
            tile.paste(source, offset)
            canvas.paste(tile, (x + 12, y))
            draw.rounded_rectangle(
                (
                    x + 11,
                    y - 1,
                    x + 12 + THUMB_SIZE,
                    y + THUMB_SIZE,
                ),
                radius=10,
                outline=(55, 69, 80),
                width=2,
            )

    draw.line(
        (48, 1298, CANVAS_WIDTH - 48, 1298),
        fill=(48, 62, 73),
        width=2,
    )
    draw.text(
        (50, 1318),
        "Review candidates only — production prefabs are not replaced.",
        font=footer_font,
        fill=(113, 132, 147),
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT, format="PNG", optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
