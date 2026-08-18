"""Blender authoring compatibility checks for the V6 asset pipeline."""

import platform

import bpy


SUPPORTED_VERSION = (5, 2)
SUPPORTED_VERSION_LABEL = "5.2.x"
FBX_EXPORTER = "bpy.ops.export_scene.fbx (Legacy FBX)"
EEVEE_ENGINE = "BLENDER_EEVEE"


def _text(value):
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)


def require_v6_pipeline():
    actual = tuple(bpy.app.version[:2])
    if actual != SUPPORTED_VERSION:
        raise RuntimeError(
            "AnalogInstrumentMR V6 authoring requires Blender "
            f"{SUPPORTED_VERSION_LABEL}; running {bpy.app.version_string}."
        )

    if not hasattr(bpy.ops.export_scene, "fbx"):
        raise RuntimeError(
            "The Legacy FBX exporter is unavailable. Enable Blender's bundled "
            "FBX extension before running the V6 pipeline."
        )

    scene = bpy.context.scene
    previous_engine = scene.render.engine
    try:
        scene.render.engine = EEVEE_ENGINE
    except (TypeError, ValueError) as exception:
        raise RuntimeError(
            f"The V6 preview pipeline requires the {EEVEE_ENGINE} render engine."
        ) from exception
    finally:
        scene.render.engine = previous_engine

    material = bpy.data.materials.new("[AnalogMR 5.2 Preflight]")
    try:
        material.use_nodes = True
        shader = next(
            (
                node
                for node in material.node_tree.nodes
                if node.type == "BSDF_PRINCIPLED"
            ),
            None,
        )
        required_inputs = ("Base Color", "Metallic", "Roughness", "Normal")
        missing = [
            name
            for name in required_inputs
            if shader is None or shader.inputs.get(name) is None
        ]
        if missing:
            raise RuntimeError(
                "Principled BSDF is missing required inputs: " + ", ".join(missing)
            )
    finally:
        bpy.data.materials.remove(material)

    print(
        "[BlenderCompat] "
        f"Blender {bpy.app.version_string}; {FBX_EXPORTER}; preflight PASS"
    )


def provenance():
    return {
        "blender_version": bpy.app.version_string,
        "blender_build_hash": _text(bpy.app.build_hash),
        "python_version": platform.python_version(),
        "fbx_exporter": FBX_EXPORTER,
        "preview_render_engine": EEVEE_ENGINE,
        "pipeline_version": "AnalogInstrumentMR Blender 5.2 migration v1",
    }
