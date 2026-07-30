"""Create an 11-object x 3-theme V6 PBR OFF/ON review sheet."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/images/AnalogInstrumentMR_V6_Material_11x3_OffOn.png"
THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
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
THEME_LABELS = {
    "OrbitalAnalog": "ORBITAL ANALOG",
    "ForgeBrass": "FORGE BRASS",
    "KineticSafety": "KINETIC SAFETY",
}
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


def source_path(theme, key, state):
    return (
        ROOT
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"Preview_{key}_{theme}_V6_Material{state}.png"
    )


def main():
    image = Image.new("RGB", (4260, 2630), (9, 14, 20))
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(FONT_BOLD, 48)
    subtitle = ImageFont.truetype(FONT, 24)
    header = ImageFont.truetype(FONT_BOLD, 24)
    label = ImageFont.truetype(FONT_BOLD, 25)
    draw.text(
        (50, 35),
        "AnalogInstrumentMR V6 — PBR Material Prototype",
        font=title,
        fill=(238, 244, 248),
    )
    draw.text(
        (52, 103),
        "Shared 2×2 atlas per theme: body / metal / gasket / emissive readout",
        font=subtitle,
        fill=(153, 171, 184),
    )
    left, top = 250, 240
    cell_width, row_height = 360, 360
    preview = 330
    for column, key in enumerate(OBJECTS):
        text = OBJECT_LABELS[key]
        box = draw.textbbox((0, 0), text, font=header)
        x = (
            left
            + column * cell_width
            + (cell_width - (box[2] - box[0])) / 2
        )
        draw.text((x, top - 48), text, font=header, fill=(205, 218, 227))
    for row, theme in enumerate(THEMES):
        for state_row, state in enumerate(("Off", "On")):
            row_index = row * 2 + state_row
            y = top + row_index * row_height
            draw.multiline_text(
                (34, y + 115),
                THEME_LABELS[theme].replace(" ", "\n") + f"\n{state.upper()}",
                font=label,
                fill=(185, 201, 212),
                spacing=7,
            )
            for column, key in enumerate(OBJECTS):
                x = (
                    left
                    + column * cell_width
                    + (cell_width - preview) // 2
                )
                source = Image.open(
                    source_path(theme, key, state)
                ).convert("RGB")
                source = source.resize(
                    (preview, preview),
                    Image.Resampling.LANCZOS,
                )
                image.paste(source, (x, y + 10))
                draw.rounded_rectangle(
                    (x - 1, y + 9, x + preview + 1, y + preview + 11),
                    radius=10,
                    outline=(56, 72, 85),
                    width=2,
                )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
