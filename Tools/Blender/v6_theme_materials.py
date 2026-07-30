"""Apply the V6 theme texture atlases to existing Blender materials."""

from pathlib import Path

import bpy


ROLE_OFFSETS = {
    "body": (0.0, 0.5, 0.5),
    "metal": (0.5, 0.5, 0.5),
    "gasket": (0.0, 0.0, 0.0),
    "readout": (0.5, 0.0, 0.0),
}

EMISSION_STRENGTH = {
    "OrbitalAnalog": 3.2,
    "ForgeBrass": 2.8,
    "KineticSafety": 3.4,
}

ROLE_VALUES = {
    "OrbitalAnalog": {
        "body": ((0.52, 0.55, 0.56, 1.0), 0.08, 0.62),
        "metal": ((0.45, 0.49, 0.51, 1.0), 0.92, 0.30),
        "gasket": ((0.055, 0.065, 0.070, 1.0), 0.00, 0.84),
        "readout": ((0.020, 0.070, 0.085, 1.0), 0.04, 0.38),
    },
    "ForgeBrass": {
        "body": ((0.115, 0.095, 0.070, 1.0), 0.72, 0.78),
        "metal": ((0.21, 0.16, 0.085, 1.0), 0.94, 0.44),
        "gasket": ((0.055, 0.058, 0.060, 1.0), 0.05, 0.82),
        "readout": ((0.105, 0.035, 0.008, 1.0), 0.02, 0.42),
    },
    "KineticSafety": {
        "body": ((0.035, 0.070, 0.105, 1.0), 0.24, 0.70),
        "metal": ((0.075, 0.095, 0.115, 1.0), 0.90, 0.48),
        "gasket": ((0.025, 0.028, 0.030, 1.0), 0.00, 0.88),
        "readout": ((0.008, 0.065, 0.080, 1.0), 0.02, 0.34),
    },
}

EMISSION_COLORS = {
    "OrbitalAnalog": (0.10, 0.68, 0.78, 1.0),
    "ForgeBrass": (0.78, 0.28, 0.025, 1.0),
    "KineticSafety": (0.02, 0.62, 0.76, 1.0),
}

SCALE_PROFILES = {
    "Standard": {
        "texture_suffix": "",
        "material_suffix": "",
        "normal_strength": 0.28,
    },
    "Medium": {
        "texture_suffix": "_Medium",
        "material_suffix": "_Medium",
        "normal_strength": 0.25,
    },
    "Large": {
        "texture_suffix": "_Large",
        "material_suffix": "_Large",
        "normal_strength": 0.22,
    },
}


def load_image(path, non_color=False):
    image = bpy.data.images.get(path.name)
    if image is None:
        image = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    return image


def input_named(shader, *names):
    for name in names:
        value = shader.inputs.get(name)
        if value is not None:
            return value
    return None


def configure_material(
    material,
    role,
    base_image,
    normal_image,
    metallic_smoothness_image,
    emission_image,
    emission_strength,
    theme,
    scale_class,
):
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texture_coordinate = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.vector_type = "POINT"
    mapping.inputs["Location"].default_value = ROLE_OFFSETS[role]
    mapping.inputs["Scale"].default_value = (0.5, 0.5, 1.0)
    links.new(texture_coordinate.outputs["Generated"], mapping.inputs["Vector"])

    def texture_node(name, image):
        node = nodes.new("ShaderNodeTexImage")
        node.name = name
        node.image = image
        node.extension = "REPEAT"
        node.interpolation = "Linear"
        node.projection = "BOX"
        node.projection_blend = 0.16
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        return node

    base = texture_node("V6 Base Color", base_image)
    normal = texture_node("V6 Normal", normal_image)
    packed = texture_node("V6 Metallic Smoothness", metallic_smoothness_image)
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = SCALE_PROFILES[
        scale_class
    ]["normal_strength"]
    separate = nodes.new("ShaderNodeSeparateColor")
    roughness = nodes.new("ShaderNodeMath")
    roughness.operation = "SUBTRACT"
    roughness.inputs[0].default_value = 1.0

    base_color, metallic_value, roughness_value = ROLE_VALUES[theme][role]
    shader.inputs["Base Color"].default_value = base_color
    shader.inputs["Metallic"].default_value = metallic_value
    shader.inputs["Roughness"].default_value = roughness_value
    links.new(base.outputs["Color"], shader.inputs["Base Color"])
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    links.new(packed.outputs["Color"], separate.inputs["Color"])
    links.new(separate.outputs["Red"], shader.inputs["Metallic"])
    links.new(packed.outputs["Alpha"], roughness.inputs[1])
    links.new(roughness.outputs["Value"], shader.inputs["Roughness"])

    if role == "readout":
        emission = texture_node("V6 Emission", emission_image)
        emission_color = input_named(shader, "Emission Color", "Emission")
        emission_power = input_named(shader, "Emission Strength")
        if emission_color is not None:
            emission_color.default_value = EMISSION_COLORS[theme]
        if emission_power is not None:
            emission_power.default_value = emission_strength

    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    material["v6_material_role"] = role
    material["v6_texture_policy"] = "shared 2x2 theme atlas"
    material["v6_model_scale_class"] = scale_class
    return material


def apply(project_root, theme, scale_class="Standard"):
    project_root = Path(project_root)
    profile = SCALE_PROFILES[scale_class]
    texture_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/Themes"
        / theme
        / "Textures/ThemeMaterialV6"
    )
    prefix = f"T_{theme}_V6_Atlas{profile['texture_suffix']}"
    base_image = load_image(texture_dir / f"{prefix}_BaseColor.png")
    normal_image = load_image(
        texture_dir / f"{prefix}_Normal.png",
        non_color=True,
    )
    packed_image = load_image(
        texture_dir / f"{prefix}_MetallicSmoothness.png",
        non_color=True,
    )
    emission_image = load_image(
        texture_dir / f"{prefix}_Emission.png",
        non_color=False,
    )

    materials = {}
    suffixes = {
        "body": "_V5_Body",
        "metal": "_V5_Metal",
        "readout": "_V5_Readout",
    }
    for role, suffix in suffixes.items():
        prefix = f"MAT_{theme}{suffix}{profile['material_suffix']}"
        matches = [
            item
            for item in bpy.data.materials
            if item.name == prefix or item.name.startswith(prefix + ".")
        ]
        if not matches:
            matches = [bpy.data.materials.new(prefix)]
        for material in matches:
            configure_material(
                material,
                role,
                base_image,
                normal_image,
                packed_image,
                emission_image,
                EMISSION_STRENGTH[theme],
                theme,
                scale_class,
            )
        materials[role] = matches[0]

    gasket_name = (
        f"MAT_{theme}_V6_Gasket{profile['material_suffix']}"
    )
    gasket = bpy.data.materials.get(gasket_name)
    if gasket is None:
        gasket = bpy.data.materials.new(gasket_name)
    materials["gasket"] = configure_material(
        gasket,
        "gasket",
        base_image,
        normal_image,
        packed_image,
        emission_image,
        EMISSION_STRENGTH[theme],
        theme,
        scale_class,
    )
    return materials


def assign_special_roles(root, materials):
    gasket_tokens = ("gasket", "washer", "bushing", "pivot_boot")
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        if any(token in obj.name.lower() for token in gasket_tokens):
            obj.data.materials.clear()
            obj.data.materials.append(materials["gasket"])


def set_emission_enabled(enabled):
    for material in bpy.data.materials:
        if material.get("v6_material_role") != "readout":
            continue
        shader = next(
            (
                node
                for node in material.node_tree.nodes
                if node.type == "BSDF_PRINCIPLED"
            ),
            None,
        )
        if shader is None:
            continue
        strength = input_named(shader, "Emission Strength")
        if strength is not None:
            strength.default_value = (
                EMISSION_STRENGTH[
                    next(
                        theme
                        for theme in EMISSION_STRENGTH
                        if theme in material.name
                    )
                ]
                if enabled
                else 0.0
            )
