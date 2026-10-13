"""Protect the accepted hair/hood correction and intentional costume assembly."""
import hashlib
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import ROOT
from analyze_assets import parsed_mesh


class AcceptedHairRegression(unittest.TestCase):
    def test_accepted_hair_weights_preserve_geometry_and_target_rig(self):
        relative = Path("natives/stm/character/ch/ch02/0200/20/00/ch0200_20_00.mesh.250925211")
        accepted = ROOT / "mod/BelaGrace_RE9_0.1.2" / relative
        self.assertEqual(hashlib.sha256(accepted.read_bytes()).hexdigest(),
                         "339bed5b5067b5118abf5823703a327754838643ebad93e9aef5e7118c3a3d4d")
        _, original = parsed_mesh(ROOT / "mod/BelaGrace_RE9" / relative)
        _, current = parsed_mesh(accepted)
        self.assertEqual(len(current.skeleton.boneList), 611)
        for a, b in zip(original.skeleton.boneList, current.skeleton.boneList):
            self.assertEqual((a.boneName, a.parentIndex), (b.boneName, b.parentIndex))
            for attr in ["worldMatrix", "localMatrix", "inverseMatrix"]:
                self.assertTrue(np.array_equal(getattr(a, attr).matrix, getattr(b, attr).matrix))
        before = [s for g in original.mainMeshLODList[0].visconGroupList for s in g.subMeshList]
        after = [s for g in current.mainMeshLODList[0].visconGroupList for s in g.subMeshList]
        self.assertEqual(len(before), len(after))
        self.assertEqual(original.materialNameList, current.materialNameList)
        influences = set()
        for a, b in zip(before, after):
            for attr in ["vertexPosList", "faceList", "uvList", "normalList", "tangentList"]:
                self.assertTrue(np.array_equal(getattr(a, attr), getattr(b, attr)), attr)
            for ids, weights in zip(b.weightIndicesList, b.weightList):
                influences.update(current.skeleton.weightedBones[i] for i, w in zip(ids, weights) if w > 0)
        self.assertIn("Head_0", influences)
        self.assertTrue(any(n.startswith("Neck_") for n in influences))
        self.assertTrue(any("Clavicle" in n for n in influences))
        alternate = ROOT / "mod/BelaGrace_RE9_0.1.2/natives/stm/character/ch/ch02/0200/21/00/ch0200_21_00.mesh.250925211"
        self.assertEqual(accepted.read_bytes(), alternate.read_bytes())


if __name__ == "__main__":
    unittest.main()

