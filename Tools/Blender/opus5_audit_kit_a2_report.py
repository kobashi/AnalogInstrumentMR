"""Audit kit A2: the migrated checks, each proved against a known defect.

Moving a check into the kit is not the point; a check nobody has seen fire is
worth nothing. Every check consolidated here is run against the asset that
failed for that reason and the asset that fixed it, and has to tell them
apart. Where no such pair was ever shipped - the pose sweep, whose failures
were all caught in smoke tests before export - a known mutation is applied to
a good asset instead.

Writes only to ArtSource/Blender/BrushUp/Opus5/AuditKit/A2/.

Usage::

    "/Applications/Blender 5.2.app/Contents/MacOS/Blender" --background \
      --factory-startup --python \
      Tools/Blender/opus5_audit_kit_a2_report.py -- --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_audit_kit as kit
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_brushup_kinetic_review as review
import opus5_theme4_full_p6_batch_c as bc
import opus5_theme4_full_p6_batch_c_r1 as cr1
import opus5_theme4_full_p6_batch_b_r1 as br1
import opus5_theme4_fastener_access_r1 as fa
import opus5_theme4_full_p6_batch_a as ba

TREE = "ArtSource/Blender/BrushUp/Opus5/AuditKit/A2"
OUTPUT = f"{TREE}/audit_kit_a2.json"
D = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def mesh_triangles(objects):
    out = []
    for obj in objects:
        tris, _ = kit.world_triangles(obj)
        out.extend(tris)
    return out


def build_parts(builder, moved=None):
    """Part-level geometry, which a joined FBX cannot give back.

    seat_probe and tool_path both have to exclude the fastener from what they
    cast against. After the body join the fastener is the same mesh as the
    panel, so the ray hits the screw head and every position measures as
    blocked. Running the generator read-only is the only way to get the parts
    apart; nothing is written and no frozen file is edited.
    """
    p1.clear_scene()
    review.configure_scene()
    material = p1.proto.make_material("audit", bc.NEUTRAL)
    saved = None
    if moved is not None:
        original = p1.fastener

        def patched(name, centre, y_face, radius, depth):
            key = moved.get(name)
            return original(name, key[0] if key else centre,
                            key[1] if key else y_face, radius, depth)

        p1.fastener = patched
        saved = original
    try:
        body, mover, movers, audit, parts = fa.capture(builder, material)
    finally:
        if saved is not None:
            p1.fastener = saved
    return parts, movers


def parts_bvh(parts, exclude):
    tris = [t for name, group in parts.items()
            if not name.startswith(exclude)
            for t in group]
    verts, faces = [], []
    for triangle in tris:
        offset = len(verts)
        verts.extend(Vector(tuple(float(c) for c in point))
                     for point in triangle)
        faces.append((offset, offset + 1, offset + 2))
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromPolygons(verts, faces, all_triangles=True), [
        [Vector(tuple(float(c) for c in point)) for point in triangle]
        for triangle in tris]


def seat_case(project_root):
    """§326: the window meter screw whose seat lay on the nameplate."""
    stages = [
        ("before", None, (-0.5480, -0.3230)),
        ("after", {"screw_-1_-1": ((-0.5540, -0.3120), bc.WM_FACE_Y)},
         (-0.5540, -0.3120)),
    ]
    rows = {}
    for stage, moved, centre in stages:
        parts, _ = build_parts(bc.build_window_meter, moved)
        tree, _ = parts_bvh(parts, "screw_-1_-1")
        seat, seat_ok = kit.seat_probe(tree, centre, bc.WM_FACE_Y, 0.0120)
        pen, pen_ok = kit.penetration_probe(tree, centre, bc.WM_FACE_Y,
                                            0.0012)
        verdict = kit.Verdict(f"WindowMeter screw_-1_-1 {stage}")
        verdict.add("seat", seat, seat_ok)
        verdict.add("penetration", pen, pen_ok)
        rows[stage] = {"source": "generator, part level",
                       "centre_xz_m": list(centre), **verdict.to_dict()}
    return {
        "check": "seat_probe + penetration_probe",
        "known_defect": ("§326: centre gap 0, ring spread 6.2 mm because the "
                         "seat lay on the plate label"),
        "requires": "part-level geometry; a joined FBX cannot be used",
        "stages": rows,
        "discriminates": (rows["before"]["pass"] is False
                          and rows["after"]["pass"] is True),
    }


def tool_case(project_root):
    """§315: the button screws the shell stood in front of."""
    centre = (-0.0560, -0.0560)
    stages = [("before", None, -0.0165), ("after", "relocate", -0.0430)]
    rows = {}
    for stage, mode, face in stages:
        moved = None
        if mode == "relocate":
            moved = {f"screw_{sx}_{sz}": ((float(sx) * 0.0560,
                                           float(sz) * 0.0560), -0.0430)
                     for sx in (-1, 1) for sz in (-1, 1)}
        parts, _ = build_parts(br1.build_button, moved)
        _, tris = parts_bvh(parts, "screw_-1_-1")
        shaft, shaft_ok = kit.tool_path(tris, centre, face, kit.TOOL_SHAFT_R)
        clear, clear_ok = kit.tool_path(tris, centre, face, kit.TOOL_CLEAR_R)
        verdict = kit.Verdict(f"Button screw_-1_-1 {stage}")
        verdict.add("shaft", shaft, shaft_ok)
        verdict.add("clearance", clear, clear_ok)
        rows[stage] = {"source": "generator, part level",
                       "seat_face_y_m": face, **verdict.to_dict()}
    return {
        "check": "tool_path",
        "known_defect": "§315: shaft and clearance blocked by the shell",
        "requires": "part-level geometry; a joined FBX cannot be used",
        "stages": rows,
        "discriminates": (rows["before"]["pass"] is False
                          and rows["after"]["pass"] is True),
    }


def uv_case(project_root):
    """§317: the packer relaid every island when parts were removed."""
    reference_path = (f"{D}/fastener_access_r1/"
                      "SM_Rotary_MachinedErgonomics_V6_Opus5_FA_R1.fbx")
    cases = [("repacked", f"{D}/fastener_access_r2/"
              "SM_Rotary_MachinedErgonomics_V6_Opus5_FA_R2.fbx"),
             ("restored", f"{D}/fastener_access_r3/"
              "SM_Rotary_MachinedErgonomics_V6_Opus5_FA_R3.fbx")]
    reference = kit.load_fbx(project_root / reference_path)
    stored = []
    for obj in reference:
        tris, _ = kit.world_triangles(obj)
        stored.append((obj.name.split(".")[0], obj))
    rows = {}
    for stage, path in cases:
        target = project_root / path
        if not target.exists():
            rows[stage] = {"missing": path}
            continue
        # Reference has to be re-imported alongside, so both live at once.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(project_root / reference_path))
        reference_objects = [o for o in bpy.data.objects if o.type == "MESH"]
        for obj in reference_objects:
            obj.name = f"REF_{obj.name}"
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(target))
        candidate_objects = [o for o in bpy.data.objects
                             if o.type == "MESH" and o not in before]
        for obj in reference_objects:
            obj.name = obj.name[4:]
        bpy.context.view_layer.update()
        totals, ok = kit.uv_carry(candidate_objects, reference_objects)
        verdict = kit.Verdict(f"Rotary UV {stage}")
        verdict.add("uv_carry", totals, ok)
        rows[stage] = {"fbx": path, "sha256": m1.digest(target),
                       **verdict.to_dict()}
    return {
        "check": "uv_carry",
        "reference": reference_path,
        "known_defect": "§317: 872 body triangles repainted on the rotary",
        "stages": rows,
        "discriminates": (rows.get("repacked", {}).get("pass") is False
                          and rows.get("restored", {}).get("pass") is True),
    }


def pose_case(project_root):
    """No shipped pair exists, so a known mutation stands in for one.

    Every pose-sweep failure this project had was caught before export, which
    means there is nothing on disk that fails. Pushing the needle 12 mm back
    into the body reproduces exactly the fault the Batch C smoke test found,
    and the check has to see it.
    """
    path = (f"{D}/batch_c_r2/"
            "SM_WindowMeter_MachinedErgonomics_V6_Opus5_P6C_R2.fbx")
    target = project_root / path
    rows = {}
    for stage, offset in (("unmutated", 0.0), ("mutated", 0.012)):
        objects = kit.load_fbx(target)
        mover = next((o for o in objects
                      if o.name.split(".")[0] == "needle"), None)
        if mover is None:
            rows[stage] = {"missing": "needle"}
            continue
        statics = [o for o in objects if o is not mover]
        if offset:
            mover.matrix_world.translation.y += offset
            bpy.context.view_layer.update()
        measurements, ok = kit.pose_interference(
            mover, statics, "Y", -115.0, 115.0, steps=48)
        measurements["mutation_offset_mm"] = round(offset * 1000.0, 2)
        verdict = kit.Verdict(f"WindowMeter needle {stage}")
        verdict.add("pose_interference", measurements, ok)
        rows[stage] = {"fbx": path, **verdict.to_dict()}
    return {
        "check": "pose_interference",
        "known_defect": ("no shipped failure exists; the needle is pushed "
                         "12 mm into the body, which is the fault the Batch C "
                         "smoke test caught before export"),
        "stages": rows,
        "discriminates": (rows.get("unmutated", {}).get("pass") is True
                          and rows.get("mutated", {}).get("pass") is False),
    }


def linear_pose_case(project_root):
    """The fixture for the instruments that slide instead of turning.

    Two contracts say `motion: translate`: PowerSlider, which travels
    +-0.09 m on its rail, and Button, which presses 0.014 m into its housing.
    §362 allows one fixture to stand for the check, and PowerSlider is the
    stronger subject - its travel is six times Button's, so a mutation has
    further to hide. The check it proves is applied to both in the sweep.

    §361 asks that a linear check be trusted only after it separates a known
    good original from a manufactured interference, exactly as the rotational
    one was. The range is taken from the Batch A contract rather than chosen
    here, and the mutation is the needle fixture's: push the moving part
    12 mm back into the body along the depth axis.
    """
    contract = ba.CONTRACT["PowerSlider"]
    low, high = contract["blender_range_m"]
    path = (f"{D}/batch_a_r4_b3u_r2/"
            "SM_PowerSlider_MachinedErgonomics_V6_Opus5_R4_B3U_R2.fbx")
    target = project_root / path
    rows = {}
    for stage, offset in (("unmutated", 0.0), ("mutated", 0.012)):
        objects = kit.load_fbx(target)
        mover = next((o for o in objects
                      if o.name.split(".")[0] == contract["moving"]), None)
        if mover is None:
            rows[stage] = {"missing": contract["moving"]}
            continue
        statics = [o for o in objects if o is not mover]
        if offset:
            mover.matrix_world.translation.y += offset
            bpy.context.view_layer.update()
        measurements, ok = kit.linear_interference(
            mover, statics, contract["blender_axis"], float(low), float(high),
            steps=48)
        measurements["mutation_offset_mm"] = round(offset * 1000.0, 2)
        measurements["range_source"] = "batch_a CONTRACT['PowerSlider']"
        verdict = kit.Verdict(f"PowerSlider {contract['moving']} {stage}")
        verdict.add("linear_interference", measurements, ok)
        rows[stage] = {"fbx": path, **verdict.to_dict()}
    return {
        "check": "linear_interference",
        "known_defect": ("PowerSlider and Button both declare `motion: "
                         "translate`; the rotational sweep could judge "
                         "neither and was counting both as having no moving "
                         "part. This fixture proves the check on PowerSlider, "
                         "whose travel is the longer of the two, and the "
                         "sweep applies it to both. The mover is pushed 12 mm "
                         "into the body, the same manufactured fault as the "
                         "needle"),
        "stages": rows,
        "discriminates": (rows.get("unmutated", {}).get("pass") is True
                          and rows.get("mutated", {}).get("pass") is False),
    }


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    tree.mkdir(parents=True, exist_ok=True)

    cases = {
        "seat": seat_case(project_root),
        "tool_access": tool_case(project_root),
        "uv_carry": uv_case(project_root),
        "pose_interference": pose_case(project_root),
        "linear_interference": linear_pose_case(project_root),
    }
    payload = {
        "phase": "AuditKit-A2",
        "purpose": ("consolidate the per-batch checks into the kit, and prove "
                    "each one against the defect it was written for"),
        "module": "Tools/Blender/opus5_audit_kit.py",
        "driver": "Tools/Blender/opus5_audit_kit_a2_report.py",
        "audit_scripts_sha256": kit.script_digests([
            Path(kit.__file__), Path(__file__)]),
        "checks_run": sorted(cases),
        "verdict_values": list(kit.VERDICT_VALUES),
        "scope": {"writes": [f"{TREE}/**"], "reads": ["shipped FBX"],
                  "untouched": ["production", "Assets/", "Builds/", "docs/",
                                "git", "frozen generators"],
                  "external_libraries": "none"},
        "cases": cases,
        "migrated_from": {
            "seat": "batch_c_r1 / fastener_access_r4",
            "tool_access": "fastener_access_r1",
            "uv_carry": "fastener_access_r3 / r4",
            "pose_interference": "batch_a, batch_b and batch_c, three copies",
            "linear_interference": ("new in §361; no per-batch audit ever "
                                    "covered the travel of PowerSlider or "
                                    "Button, the two translate contracts"),
        },
    }
    # A fixture that cannot separate the known good original from the
    # manufactured defect leaves its check unproven. §361 is explicit that
    # such a check is not promoted to blocking: it is REVIEW, not FAIL.
    tally = kit.Tally("a2_back_test", len(cases))
    for name, row in sorted(cases.items()):
        tally.record(name, kit.PASS if row["discriminates"] else kit.REVIEW,
                     None if row["discriminates"]
                     else "fixture did not separate original from mutation; "
                          "check stays advisory and is not promoted to "
                          "blocking")
    payload["tally"] = tally.to_dict()
    payload["promoted_to_blocking"] = sorted(
        name for name, row in cases.items() if row["discriminates"])
    payload["status"] = ("audit_kit_a2_ready"
                         if all(row["discriminates"]
                                for row in cases.values())
                         else "audit_kit_a2_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    for name, row in cases.items():
        print(f"[A2] {name:18s} discriminates {row['discriminates']}")
        for stage, entry in row["stages"].items():
            if "missing" in entry:
                print(f"       {stage:10s} MISSING {entry['missing']}")
                continue
            print(f"       {stage:10s} pass {entry['pass']} "
                  f"failing {entry['failing']}")
    print(f"[A2] status {payload['status']}")


if __name__ == "__main__":
    main()
