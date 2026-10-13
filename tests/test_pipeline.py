import io
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import numpy as np
from PIL import Image
from common import confined, reader, ROOT
from rigging import sanitize_weights, rest_transform, fit_vertices, bone_mapping, landmark_transform, packed_tangents
from build_materials import acot_from_atoc, relocated_native_material, make_preset
from garment_weights import lower_garment_weights
from garment_surface import diffuse_weights, clearance_offset


class PipelineTests(unittest.TestCase):
    def test_diffusion_preserves_constant_weights_and_does_not_move_vertices(self):
        points = np.asarray([[0, 0, 0], [.1, 0, 0], [0, .1, 0], [5, 5, 5]], float)
        original = points.copy()
        rows = [[("Hip", .4), ("L_Leg_Upper", .6)]] * 4
        values, stats = diffuse_weights(points, [[0, 1, 2]], rows, 10, 1.0, .15)
        self.assertTrue(np.array_equal(original, points))
        for pairs in values:
            self.assertAlmostEqual(dict(pairs)["Hip"], .4)
            self.assertAlmostEqual(dict(pairs)["L_Leg_Upper"], .6)
        self.assertFalse(stats["geometry_welded"])

    def test_clearance_is_bounded_radial_and_fades_at_band_limits(self):
        settings = {"amount_m": .025, "lower_start": .6, "lower_fade_width": .2, "upper_end": 1.02, "upper_fade_width": .14}
        offset = clearance_offset([.2, .84, .1], settings)
        self.assertAlmostEqual(np.linalg.norm(offset), .025)
        self.assertEqual(offset[1], 0)
        for height in [.1, .6, 1.02, 1.2]:
            self.assertTrue(np.array_equal(clearance_offset([.2, height, .1], settings), [0, 0, 0]))

    def test_lower_garment_preserves_pelvis_and_nonleg_influences(self):
        parameters = {"knee_max": .6, "hip_width": .12, "knee_offset": .28, "knee_width": .6,
                      "side_width": .32, "transition_offset": .25, "transition_width": .32}
        pairs = [("Hip", .3), ("Spine_0", .4), ("L_Leg_Upper", .3)]
        self.assertEqual(dict(lower_garment_weights([.1, 1.0, 0], pairs, .95, .5, parameters)), dict(pairs))
        lower = dict(lower_garment_weights([.3, .1, 0], [("L_Leg_Foot", .6), ("Spine_0", .4)], .95, .5, parameters))
        self.assertNotIn("L_Leg_Foot", lower)
        self.assertAlmostEqual(lower["Spine_0"], .4)
        self.assertAlmostEqual(sum(lower.values()), 1)

    def test_lower_garment_field_has_mirror_symmetry_and_rejects_bad_width(self):
        parameters = {"knee_max": .6, "hip_width": .12, "knee_offset": .28, "knee_width": .6,
                      "side_width": .32, "transition_offset": .25, "transition_width": .32}
        a = dict(lower_garment_weights([.3, .1, 0], [("L_Leg_Foot", 1)], .95, .5, parameters))
        b = dict(lower_garment_weights([-.3, .1, 0], [("R_Leg_Foot", 1)], .95, .5, parameters))
        self.assertAlmostEqual(a["L_Leg_Lower"], b["R_Leg_Lower"])
        self.assertAlmostEqual(a["L_Leg_Upper"], b["R_Leg_Upper"])
        with self.assertRaises(ValueError):
            lower_garment_weights([.3, .1, 0], [("Hip", 1)], .95, .5, dict(parameters, side_width=0))

    def test_weight_merge_and_budget(self):
        pairs = [("Hip", .3), ("Hip", .2), ("Spine", .5)]
        self.assertEqual(dict(sanitize_weights(pairs)), {"Hip": .5, "Spine": .5})
        result = sanitize_weights([(str(i), i + 1) for i in range(12)])
        self.assertEqual(len(result), 8)
        self.assertAlmostEqual(sum(w for _, w in result), 1)

    def test_bad_weights_fail(self):
        for pairs in [[("x", 0)], [("x", -1)], [("x", float("nan"))]]:
            with self.assertRaises(ValueError):
                sanitize_weights(pairs)

    def test_rest_transform_rotated_translation(self):
        source = np.eye(4)
        source[0, 3] = 2
        target = np.array([[0, -1, 0, 0], [1, 0, 0, 3], [0, 0, 1, 0], [0, 0, 0, 1]], float)
        transform = rest_transform(source, target)
        self.assertTrue(np.allclose(transform @ [3, 0, 0, 1], [0, 4, 0, 1]))
        fitted = fit_vertices([[3, 0, 0]], [[0]], [[1]], ["bone"], {"bone": transform})
        self.assertTrue(np.allclose(fitted, [[0, 4, 0]]))

    def test_mask_channel_swizzle(self):
        image = Image.new("RGBA", (1, 1), (10, 20, 30, 40))
        self.assertEqual(acot_from_atoc(image).getpixel((0, 0)), (10, 40, 30, 20))

    def test_landmark_transform_ignores_joint_roll_and_fits_length(self):
        transform = landmark_transform([1, 0, 0], [0, 3, 0], [2, 0, 0], [0, 5, 0], .8)
        self.assertTrue(np.allclose(transform @ [1, 0, 0, 1], [0, 3, 0, 1]))
        self.assertTrue(np.allclose(transform @ [2, 0, 0, 1], [0, 5, 0, 1]))
        self.assertTrue(np.allclose(transform @ [1, 0, 1, 1], [0, 3, .8, 1]))

    def test_path_traversal_fails(self):
        with self.assertRaises(ValueError):
            confined(Path.cwd(), "../outside")

    def test_native_tangent_roundtrip_preserves_direction_and_sign(self):
        writer = reader("RE-Mesh-Editor", "remesh", "modules.mesh.file_re_mesh")
        parser = reader("RE-Mesh-Editor", "remesh", "modules.mesh.re_mesh_parse")
        stream = io.BytesIO()
        direction = np.array([[.6, .8, 0, -1]], float)
        writer.WriteToNorTanBuffer(stream, [[0, 0, 1]], packed_tangents(direction))
        normals, tangents = parser.ReadNorTanBuffer(stream.getvalue(), [])
        self.assertTrue(np.allclose(tangents[0], direction[0, :3], atol=1 / 127))
        self.assertGreater(np.linalg.norm(tangents[0]), .99)
        self.assertEqual(int.from_bytes(stream.getvalue()[7:8], signed=True), -127)

    def test_native_material_relocation_preserves_properties(self):
        module = reader("RE-Mesh-Editor", "remesh", "modules.mdf.file_re_mdf")
        original = next((ROOT / "assets/extracted/re9").rglob("ch0200_50_00_00.mdf2.51"))
        source = next(m for m in module.readMDF(str(original)).materialList if m.materialName == "Set00_Boots_Cloth_Mat")
        mixed = module.MDFFile()
        preset = make_preset(module, "Character", source)
        preset.materialName = "TestConvertedMaterial"
        mixed.materialList = [preset, relocated_native_material(source)]
        output = confined(ROOT, "build/tests/native_mdf_relocation.mdf2.51")
        output.parent.mkdir(parents=True, exist_ok=True)
        module.writeMDF(mixed, str(output))
        result = module.readMDF(str(output)).materialList[1]
        self.assertEqual(result.mmtrPath, source.mmtrPath)
        self.assertEqual([(p.propName, p.propValue) for p in result.propertyList], [(p.propName, p.propValue) for p in source.propertyList])
        self.assertEqual([(t.textureType, t.texturePath) for t in result.textureList], [(t.textureType, t.texturePath) for t in source.textureList])

    def test_missing_target_alias_fails(self):
        class Bone:
            boneName, parentIndex = "L_UpperArm", -1
        with self.assertRaises(ValueError):
            bone_mapping([Bone()], {"root"})


if __name__ == "__main__":
    unittest.main()

