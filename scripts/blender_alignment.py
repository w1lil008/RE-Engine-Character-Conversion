"""Inspect the assembled exported binaries under joint-specific synthetic poses.

No hole-filling or seam welding is performed. Source segmentation is intentional.
These fixtures expose deformation risks; they do not reproduce game animation.
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import math
import numpy as np
from mathutils import Vector, Quaternion
from common import ROOT, write_json, confined
from blender_scene import look_at


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", default="assets/work/BelaGrace_preparation.blend")
    parser.add_argument("--output", default="reports/alignment")
    parser.add_argument("--report", default="reports/alignment_qa.json")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    bpy.ops.wm.open_mainfile(filepath=str(confined(ROOT, args.scene)))
    scene = bpy.context.scene
    rig = bpy.data.objects["GraceOriginalBindRig"]
    camera = scene.camera
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.eevee.taa_render_samples = 32
    output = confined(ROOT, args.output)
    output.mkdir(parents=True, exist_ok=True)
    meshes = [o for o in bpy.data.collections["Bela_on_Grace_Prototype"].objects if o.type == "MESH"]

    def pose(name, axis, angle):
        pb = rig.pose.bones[name]
        local_axis = pb.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion(local_axis.normalized(), angle)

    def reset():
        for pb in rig.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion()
        for obj in meshes:
            obj.hide_render = False
        bpy.context.view_layer.update()

    def render(name, point, scale, position):
        camera.data.ortho_scale = scale
        camera.location = position
        look_at(camera, point)
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    report = {"status": "REQUIRES_VISUAL_REVIEW", "in_game_tested": False, "fixtures": [],
              "intentional_segmentation": "Body cutouts and upper/lower asset boundaries are not automatically positional failures.",
              "limits": "Finite geometry and joint landmarks do not prove cloth collision, seam closure or gameplay compatibility."}
    fixtures = [
        ("neck_shoulders_rest", [], (0, -.04, 1.38), .85, (0, -5, 1.6), False),
        ("neck_head_turn", [("Head_0", (0, 0, 1), .45), ("Neck_1", (1, 0, 0), .15)], (0, -.04, 1.43), .7, (1.3, -5, 1.6), False),
        ("shoulder_elbow_wrist_flex", [("L_Arm_Upper", (0, 1, 0), -.5), ("L_Arm_Lower", (0, 1, 0), -1.0),
                                      ("L_Arm_Hand", (0, 0, 1), .25)], (0, 0, 1.13), 1.45, (1.5, -5, 1.6), False),
        ("pelvis_knee_ankle_step", [("L_Leg_Upper", (1, 0, 0), -.5), ("L_Leg_Lower", (1, 0, 0), .8),
                                   ("L_Leg_Foot", (1, 0, 0), -.2)], (0, 0, .75), 1.8, (2.5, -5, 1.4), False),
        ("pelvis_knee_ankle_step_uncovered", [("L_Leg_Upper", (1, 0, 0), -.5), ("L_Leg_Lower", (1, 0, 0), .8),
                                             ("L_Leg_Foot", (1, 0, 0), -.2)], (0, 0, .65), 1.65, (2.5, -5, 1.3), True),
        ("ankles_rest_uncovered", [], (0, 0, .2), .65, (1.5, -5, .45), True),
        ("bilateral_arm_flex", [("L_Arm_Lower", (0, 1, 0), -.9), ("R_Arm_Lower", (0, 1, 0), .9),
                                ("L_Arm_Hand", (0, 0, 1), .3), ("R_Arm_Hand", (0, 0, 1), -.3)],
                               (0, 0, 1.15), 1.45, (0, -5, 1.6), False),
        ("bilateral_leg_flex", [("L_Leg_Upper", (1, 0, 0), -.65), ("R_Leg_Upper", (1, 0, 0), -.65),
                                ("L_Leg_Lower", (1, 0, 0), 1.1), ("R_Leg_Lower", (1, 0, 0), 1.1)],
                               (0, 0, .8), 1.9, (2.5, -5, 1.4), False),
        ("pelvis_knee_step_rear", [("L_Leg_Upper", (1, 0, 0), -.5), ("L_Leg_Lower", (1, 0, 0), .8),
                                   ("L_Leg_Foot", (1, 0, 0), -.2)], (0, 0, .75), 1.8, (0, 5, 1.4), False),
        ("bilateral_leg_flex_rear", [("L_Leg_Upper", (1, 0, 0), -.65), ("R_Leg_Upper", (1, 0, 0), -.65),
                                     ("L_Leg_Lower", (1, 0, 0), 1.1), ("R_Leg_Lower", (1, 0, 0), 1.1)],
                                    (0, 0, .8), 1.9, (0, 5, 1.4), False),
        ("crouch_side", [("L_Leg_Upper", (1, 0, 0), -1.1), ("R_Leg_Upper", (1, 0, 0), -1.1),
                         ("L_Leg_Lower", (1, 0, 0), 1.8), ("R_Leg_Lower", (1, 0, 0), 1.8)],
                        (0, 0, .8), 1.9, (5, 0, 1.4), False),
        ("crouch_rear", [("L_Leg_Upper", (1, 0, 0), -1.1), ("R_Leg_Upper", (1, 0, 0), -1.1),
                         ("L_Leg_Lower", (1, 0, 0), 1.8), ("R_Leg_Lower", (1, 0, 0), 1.8)],
                        (0, 0, .8), 1.9, (0, 5, 1.4), False),
        ("striding_legs", [("L_Leg_Upper", (1, 0, 0), -.55), ("L_Leg_Lower", (1, 0, 0), .6),
                            ("R_Leg_Upper", (1, 0, 0), .35), ("R_Leg_Lower", (1, 0, 0), .35)],
                           (0, 0, .8), 1.9, (2.5, -5, 1.4), False),
        ("leg_abduction", [("L_Leg_Upper", (0, 1, 0), -.35), ("R_Leg_Upper", (0, 1, 0), .35)],
                           (0, 0, .8), 1.9, (0, -5, 1.4), False),
    ]
    clothing_tokens = ["Dress", "Hood", "Corset", "Buttons", "CapeCatch", "Inner_Mat"]
    for name, rotations, point, scale, position, uncovered in fixtures:
        reset()
        for bone, axis, angle in rotations:
            pose(bone, axis, angle)
        for obj in meshes:
            if uncovered and any(token in obj.name for token in clothing_tokens):
                obj.hide_render = True
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        bounds, garment_strain = [], []
        for obj in meshes:
            evaluated = obj.evaluated_get(depsgraph)
            data = evaluated.to_mesh()
            points = np.array([v.co[:] for v in data.vertices])
            if not np.isfinite(points).all() or np.max(np.abs(points)) > 5:
                raise ValueError(f"Exploding/nonfinite geometry in {name}: {obj.name}")
            bounds.append({"object": obj.name, "bounds": [points.min(0).tolist(), points.max(0).tolist()]})
            if obj.data.materials[0].name.split(".")[0] in {"Dress_Mat", "DressBack_Mat"}:
                rest = np.asarray([v.co[:] for v in obj.data.vertices])
                edges = np.asarray([e.vertices[:] for e in obj.data.edges])
                lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
                valid = lengths > .0001
                ratios = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)[valid] / lengths[valid]
                garment_strain.append({"object": obj.name, "edge_ratio_p01": float(np.quantile(ratios, .01)),
                                       "edge_ratio_p99": float(np.quantile(ratios, .99)), "edge_ratio_max": float(ratios.max())})
            evaluated.to_mesh_clear()
        render(name, point, scale, position)
        report["fixtures"].append({"name": name, "pose": rotations, "clothing_hidden_for_inspection": uncovered,
                                   "finite_geometry": True, "bounds": bounds, "garment_edge_strain": garment_strain})
    reset()
    scene["ALIGNMENT_STATUS"] = "Synthetic fixture review; packaging withheld until visual review"
    report["source_scene"] = args.scene
    write_json(confined(ROOT, args.report), report)
    print(f"{len(fixtures)} joint-specific fixtures rendered. Visual review required; no game test.")


if __name__ == "__main__":
    main()

