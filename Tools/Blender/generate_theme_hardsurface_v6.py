"""Generate the V6 representative hard-surface theme set.

V6 combines the independently authored V5 theme silhouettes and mechanical
support corrections with the layered hard-surface density established by V4.
Only micro detail (engraving, knurling, wear and labels) is deferred to maps.
"""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_hardsurface_kinetic_set_v4 as v4
import generate_hardsurface_lever_retopo_v3 as retopo
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common
import generate_theme_silhouette_v5 as v5


THEMES = v5.THEMES
ASSETS = v5.ASSETS


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skip-topology", action="store_true")
    parser.add_argument("--only", nargs="+", choices=tuple(ASSETS))
    return parser.parse_args(args)


def parent_keep_world(obj, parent):
    world_matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world_matrix
    return obj


def add_fastener(root, name, x, z, outward, material, radius, vertices=10):
    fastener = v4.cylinder_y(
        name,
        radius,
        max(radius * 0.65, 0.0024),
        outward,
        material,
        vertices,
    )
    fastener.location.x = x
    fastener.location.z = z
    fastener.parent = root
    return fastener


def torus_y(
    name,
    major_radius,
    minor_radius,
    outward,
    material,
    major_segments=16,
    minor_segments=3,
):
    bpy.ops.mesh.primitive_torus_add(
        align="WORLD",
        major_segments=major_segments,
        minor_segments=minor_segments,
        location=(0.0, -outward, 0.0),
        rotation=(math.radians(90.0), 0.0, 0.0),
        major_radius=major_radius,
        minor_radius=minor_radius,
    )
    torus = bpy.context.object
    torus.name = name
    torus.data.materials.append(material)
    retopo.bevel(torus, min(minor_radius * 0.20, 0.0006), 1)
    return torus


def torus_x(
    name,
    major_radius,
    minor_radius,
    location,
    material,
    major_segments=14,
    minor_segments=3,
):
    bpy.ops.mesh.primitive_torus_add(
        align="WORLD",
        major_segments=major_segments,
        minor_segments=minor_segments,
        location=location,
        rotation=(0.0, math.radians(90.0), 0.0),
        major_radius=major_radius,
        minor_radius=minor_radius,
    )
    torus = bpy.context.object
    torus.name = name
    torus.data.materials.append(material)
    retopo.bevel(torus, min(minor_radius * 0.20, 0.0006), 1)
    return torus


def add_orbital_meter_detail(root, mats):
    gasket = torus_y(
        "orbital_v6_glass_gasket",
        0.043,
        0.0014,
        0.047,
        mats["body"],
        16,
        3,
    )
    gasket.parent = root
    step = torus_y(
        "orbital_v6_intermediate_bezel",
        0.048,
        0.0025,
        0.041,
        mats["metal"],
        16,
    )
    step.parent = root
    inner = torus_y(
        "orbital_v6_inner_retainer",
        0.045,
        0.0018,
        0.049,
        mats["body"],
        16,
    )
    inner.parent = root
    for index, (x, z) in enumerate(
        ((-0.063, -0.042), (0.063, -0.042),
         (-0.063, 0.042), (0.063, 0.042))
    ):
        add_fastener(
            root, f"orbital_v6_fastener_{index}",
            x, z, 0.024, mats["metal"], 0.0032,
        )
    for side in (-1, 1):
        for index, z in enumerate((-0.024, -0.008, 0.008, 0.024)):
            vent = v4.prism(
                f"orbital_v6_side_vent_{side}_{index}",
                0.012,
                0.005,
                0.0012,
                -0.020,
                -0.033,
                mats["metal"],
                z,
            )
            vent.location.x = side * 0.066
            vent.parent = root
    for index, angle_deg in enumerate((-60, 0, 60)):
        angle = math.radians(angle_deg)
        mark = v4.accent_bar(
            f"orbital_v6_inner_scale_{index}",
            0.0015,
            0.0045,
            math.sin(angle) * 0.031,
            math.cos(angle) * 0.031,
            0.050,
            mats["readout"],
        )
        mark.rotation_euler.y = angle
        mark.parent = root


def add_forge_meter_detail(root, mats):
    gasket = torus_y(
        "forge_v6_glass_gasket",
        0.044,
        0.0018,
        0.073,
        mats["body"],
        16,
        3,
    )
    gasket.parent = root
    flange = torus_y(
        "forge_v6_brass_flange",
        0.055,
        0.0035,
        0.070,
        mats["metal"],
        16,
    )
    flange.parent = root
    retainer = torus_y(
        "forge_v6_glass_step",
        0.047,
        0.0022,
        0.075,
        mats["body"],
        16,
    )
    retainer.parent = root
    for index in range(8):
        angle = math.radians(index * 45)
        add_fastener(
            root,
            f"forge_v6_flange_bolt_{index}",
            math.sin(angle) * 0.055,
            math.cos(angle) * 0.055,
            0.073,
            mats["metal"],
            0.0038,
            8,
        )
    for x in (-0.052, 0.052):
        gusset = v4.prism(
            "forge_v6_mount_gusset",
            0.026,
            0.034,
            0.006,
            -0.010,
            -0.041,
            mats["metal"],
            -0.055,
        )
        gusset.location.x = x
        gusset.parent = root


def add_kinetic_meter_detail(root, mats):
    gasket = torus_y(
        "kinetic_v6_glass_gasket",
        0.043,
        0.0018,
        0.076,
        mats["body"],
        12,
        3,
    )
    gasket.parent = root
    inner = torus_y(
        "kinetic_v6_inner_armor_ring",
        0.045,
        0.0030,
        0.078,
        mats["metal"],
        12,
    )
    inner.parent = root
    for index, (x, z) in enumerate(
        ((-0.057, -0.057), (0.057, -0.057),
         (-0.057, 0.057), (0.057, 0.057))
    ):
        clamp = v4.prism(
            f"kinetic_v6_corner_clamp_{index}",
            0.028,
            0.024,
            0.005,
            -0.044,
            -0.075,
            mats["metal"],
            z,
        )
        clamp.location.x = x
        clamp.parent = root
        add_fastener(
            root, f"kinetic_v6_clamp_bolt_{index}",
            x, z, 0.075, mats["body"], 0.0040, 8,
        )
    for index, x in enumerate((-0.024, 0.0, 0.024)):
        vent = v4.prism(
            f"kinetic_v6_lower_vent_{index}",
            0.014,
            0.005,
            0.001,
            -0.046,
            -0.074,
            mats["body"],
            -0.067,
        )
        vent.location.x = x
        vent.parent = root


def add_orbital_lever_detail(root, mats):
    boot = v4.prism(
        "orbital_v6_pivot_boot",
        0.070,
        0.038,
        0.007,
        -0.018,
        -0.025,
        mats["body"],
        -0.074,
    )
    boot.parent = root
    for x in (-0.023, 0.023):
        bushing = torus_x(
            "orbital_v6_pivot_bushing",
            0.011,
            0.0022,
            (x, -0.025, -0.074),
            mats["metal"],
            12,
            3,
        )
        bushing.parent = root
    detent_plate = v4.prism(
        "orbital_v6_detent_plate",
        0.022,
        0.130,
        0.004,
        -0.024,
        -0.040,
        mats["metal"],
    )
    detent_plate.location.x = 0.034
    detent_plate.parent = root
    for index, z in enumerate((-0.050, -0.025, 0.0, 0.025, 0.050)):
        detent = v4.accent_bar(
            f"orbital_v6_detent_{index}",
            0.010 if index != 2 else 0.015,
            0.0035,
            0.034,
            z,
            0.042,
            mats["readout"],
        )
        detent.parent = root
    for index, (x, z) in enumerate(
        ((-0.050, -0.085), (0.050, -0.085),
         (-0.050, 0.085), (0.050, 0.085))
    ):
        add_fastener(
            root, f"orbital_v6_lever_fastener_{index}",
            x, z, 0.030, mats["metal"], 0.0032,
        )
    handle = next(
        (obj for obj in root.children_recursive if obj.name == "handle"),
        None,
    )
    if handle is not None:
        for index, x in enumerate((-0.016, 0.0, 0.016)):
            rib = v4.prism(
                f"orbital_v6_grip_rib_{index}",
                0.004,
                0.019,
                0.001,
                -0.059,
                -0.063,
                mats["metal"],
                0.084,
            )
            rib.location.x = x
            parent_keep_world(rib, handle)


def add_forge_lever_detail(root, mats):
    for index in range(7):
        angle = math.radians(-75 + index * 25)
        mark = v4.prism(
            f"forge_v6_detent_tooth_{index}",
            0.007,
            0.014,
            0.0018,
            -0.040,
            -0.046,
            mats["metal"],
        )
        mark.location.x = math.sin(angle) * 0.055
        mark.location.z = -0.034 + math.cos(angle) * 0.055
        mark.rotation_euler.y = angle
        mark.parent = root
    for index in range(6):
        angle = math.radians(index * 60)
        add_fastener(
            root,
            f"forge_v6_lever_flange_bolt_{index}",
            math.sin(angle) * 0.064,
            math.cos(angle) * 0.064,
            0.0385,
            mats["metal"],
            0.0038,
            8,
        )
    for x in (-0.030, 0.030):
        bearing = v4.cylinder_x(
            "forge_v6_trunnion_bearing",
            0.018,
            0.020,
            (x, -0.065, -0.034),
            mats["metal"],
            16,
        )
        bearing.parent = root
        washer = torus_x(
            "forge_v6_bearing_washer",
            0.017,
            0.0025,
            (x, -0.065, -0.034),
            mats["body"],
            14,
            3,
        )
        washer.parent = root
    handle = next(
        (obj for obj in root.children_recursive if obj.name == "handle"),
        None,
    )
    if handle is not None:
        for index, z in enumerate((0.035, 0.055, 0.075)):
            ring = v4.cylinder_z(
                f"forge_v6_shaft_ring_{index}",
                0.0098,
                0.005,
                (0.0, -0.065, z),
                mats["metal"],
                14,
            )
            parent_keep_world(ring, handle)


def add_kinetic_lever_detail(root, mats):
    for index, (x, z) in enumerate(
        ((-0.073, -0.043), (0.073, -0.043),
         (-0.073, 0.043), (0.073, 0.043))
    ):
        add_fastener(
            root, f"kinetic_v6_lever_bolt_{index}",
            x, z, 0.066, mats["metal"], 0.0040, 8,
        )
    for x in (-0.032, 0.032):
        bearing = v4.cylinder_x(
            "kinetic_v6_bearing_cover",
            0.022,
            0.020,
            (x, -0.050, -0.025),
            mats["metal"],
            12,
        )
        bearing.parent = root
        washer = torus_x(
            "kinetic_v6_bearing_washer",
            0.021,
            0.0028,
            (x, -0.050, -0.025),
            mats["body"],
            10,
            3,
        )
        washer.parent = root


def add_orbital_panel_detail(root, mats):
    inner = v4.shell(
        "orbital_v6_inner_bezel",
        1.34,
        0.60,
        0.024,
        1.23,
        0.49,
        0.016,
        0.118,
        0.110,
        mats["metal"],
    )
    inner.parent = root
    for index, x in enumerate((-0.56, -0.40, -0.24, -0.08, 0.08, 0.24, 0.40, 0.56)):
        vent = v4.prism(
            f"orbital_v6_panel_vent_{index}",
            0.090,
            0.014,
            0.003,
            -0.108,
            -0.126,
            mats["body"],
            -0.330,
        )
        vent.location.x = x
        vent.parent = root
    for index, (x, z) in enumerate(
        ((-0.725, -0.330), (0.725, -0.330),
         (-0.725, 0.330), (0.725, 0.330))
    ):
        add_fastener(
            root, f"orbital_v6_panel_fastener_{index}",
            x, z, 0.108, mats["metal"], 0.010, 10,
        )
    for x in (-0.655, 0.655):
        pod = v4.prism(
            "orbital_v6_service_pod",
            0.105,
            0.210,
            0.018,
            -0.092,
            -0.132,
            mats["body"],
            -0.080,
        )
        pod.location.x = x
        pod.parent = root


def add_forge_panel_detail(root, mats):
    inner = v4.shell(
        "forge_v6_stepped_inner_frame",
        1.30,
        0.64,
        0.045,
        1.12,
        0.47,
        0.030,
        0.184,
        0.170,
        mats["metal"],
    )
    inner.parent = root
    bolt_positions = [
        (-0.72, -0.35), (-0.36, -0.39), (0.0, -0.39),
        (0.36, -0.39), (0.72, -0.35),
        (-0.72, 0.35), (-0.36, 0.39), (0.0, 0.39),
        (0.36, 0.39), (0.72, 0.35),
    ]
    for index, (x, z) in enumerate(bolt_positions):
        add_fastener(
            root, f"forge_v6_panel_bolt_{index}",
            x, z, 0.150, mats["metal"], 0.011, 8,
        )
    manifold = v4.cylinder_x(
        "forge_v6_lower_manifold",
        0.030,
        0.90,
        (0.0, -0.158, -0.365),
        mats["metal"],
        16,
    )
    manifold.parent = root
    for x in (-0.36, 0.0, 0.36):
        collar = v4.cylinder_z(
            "forge_v6_manifold_collar",
            0.043,
            0.045,
            (x, -0.158, -0.365),
            mats["body"],
            16,
        )
        collar.parent = root


def add_kinetic_panel_detail(root, mats):
    inner = v4.shell(
        "kinetic_v6_segmented_inner_bezel",
        1.32,
        0.64,
        0.055,
        1.12,
        0.45,
        0.030,
        0.202,
        0.190,
        mats["metal"],
    )
    inner.parent = root
    for index, (x, z) in enumerate(
        ((-0.690, -0.350), (0.690, -0.350),
         (-0.690, 0.350), (0.690, 0.350))
    ):
        armor = v4.prism(
            f"kinetic_v6_corner_armor_{index}",
            0.180,
            0.130,
            0.026,
            -0.140,
            -0.205,
            mats["body"],
            z,
        )
        armor.location.x = x
        armor.parent = root
        add_fastener(
            root, f"kinetic_v6_panel_bolt_{index}",
            x, z, 0.205, mats["metal"], 0.012, 8,
        )
    for index, x in enumerate((-0.48, -0.32, -0.16, 0.0, 0.16, 0.32, 0.48)):
        vent = v4.prism(
            f"kinetic_v6_panel_vent_{index}",
            0.105,
            0.020,
            0.004,
            -0.176,
            -0.207,
            mats["body"],
            -0.345,
        )
        vent.location.x = x
        vent.parent = root


DETAIL_BUILDERS = {
    ("OrbitalAnalog", "MeterRound"): add_orbital_meter_detail,
    ("ForgeBrass", "MeterRound"): add_forge_meter_detail,
    ("KineticSafety", "MeterRound"): add_kinetic_meter_detail,
    ("OrbitalAnalog", "Lever"): add_orbital_lever_detail,
    ("ForgeBrass", "Lever"): add_forge_lever_detail,
    ("KineticSafety", "Lever"): add_kinetic_lever_detail,
    ("OrbitalAnalog", "WindowPanel"): add_orbital_panel_detail,
    ("ForgeBrass", "WindowPanel"): add_forge_panel_detail,
    ("KineticSafety", "WindowPanel"): add_kinetic_panel_detail,
}


def meshes_under(root):
    return [obj for obj in root.children_recursive if obj.type == "MESH"]


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    path.with_suffix(".blend1").unlink(missing_ok=True)


def generate_one(project_root, theme, key, skip_topology):
    common.clean_scene()
    type_id, budget = ASSETS[key]
    root, pivot_position, local_axis = v5.BUILDERS[(theme, key)]()
    root.name = f"PF_Visual_{key}_{theme}_V6"
    root["art_pass"] = "V6 hybrid hard-surface prototype"
    root["quality_floor"] = "V4 hard-surface retopo"
    root["geometry_policy"] = (
        "silhouette, major layers, supports and interaction structure are mesh"
    )
    root["texture_policy"] = (
        "engraving, micro grooves, knurling, wear and labels are maps"
    )
    root["assembly_policy"] = (
        "gaskets, seams, bushings, stops and supports explain construction"
    )
    mats = v5.materials(theme)
    DETAIL_BUILDERS[(theme, key)](root, mats)
    meshes = meshes_under(root)
    common.apply_transforms(meshes)
    source_stats = retopo.topology_stats(meshes)
    if source_stats["non_manifold_edges"]:
        raise RuntimeError(f"{theme}/{key}: non-manifold source")
    if source_stats["zero_area_faces"]:
        raise RuntimeError(f"{theme}/{key}: degenerate source")

    source_dir = (
        project_root / "ArtSource/Blender/ThemeHardSurfaceV6" / theme
    )
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/RefinedCandidates"
        / theme
        / "ThemeHardSurfaceV6"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    controls.create_preview(
        meshes,
        0.0,
        source_dir / f"Preview_{key}_{theme}_V6_Grayscale.png",
    )
    if not skip_topology:
        retopo.render_topology_preview(
            meshes,
            source_dir / f"Preview_{key}_{theme}_V6_Topology.png",
        )
    save_blend(source_dir / f"BL_{key}_{theme}_V6_Retopo.blend")
    retopo.triangulate(meshes)
    final_stats = retopo.topology_stats(meshes)
    if final_stats["non_manifold_edges"]:
        raise RuntimeError(f"{theme}/{key}: non-manifold final")
    if final_stats["zero_area_faces"]:
        raise RuntimeError(f"{theme}/{key}: degenerate final")
    if final_stats["faces"] > budget:
        raise RuntimeError(
            f"{theme}/{key}: {final_stats['faces']} > {budget}"
        )
    save_blend(
        source_dir / f"BL_{key}_{theme}_V6_Triangulated.blend"
    )
    fbx_path = model_dir / f"SM_{key}_{theme}_V6_Grayscale.fbx"
    if fbx_path.with_suffix(".fbm").exists():
        shutil.rmtree(fbx_path.with_suffix(".fbm"))
    common.export_fbx(root, fbx_path)
    report = {
        "asset": f"{key}_{theme}_V6_Grayscale",
        "type_id": type_id,
        "theme_id": THEMES[theme],
        "art_pass": "V6 hybrid hard-surface prototype",
        "quality_floor": "V4 hard-surface retopo",
        "geometry_policy": (
            "silhouette, major layers, supports and interaction structure"
        ),
        "texture_policy": (
            "engraving, micro grooves, knurling, wear and labels"
        ),
        "assembly_policy": (
            "gaskets, seams, bushings, stops and supports"
        ),
        "source_topology": source_stats,
        "triangulated_topology": final_stats,
        "triangle_budget": budget,
        "pivot": {
            "position": list(pivot_position),
            "local_axis": list(local_axis),
        },
        "production_integrated": False,
        "authoring_environment": blender_compat.provenance(),
    }
    (
        source_dir / f"{key}_{theme}_V6.report.json"
    ).write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report))


def main():
    blender_compat.require_v6_pipeline()
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    only = set(args.only or ())
    for theme in THEMES:
        for key in ASSETS:
            if only and key not in only:
                continue
            generate_one(
                project_root,
                theme,
                key,
                args.skip_topology,
            )


if __name__ == "__main__":
    main()
