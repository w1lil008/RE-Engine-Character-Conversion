# v0.1.2 status before packaging — 9 October 2026

1. **Confirmed:** user-run v0.1.0 standing/weapon appearance and one cutscene's
   appearance/lighting. v0.1.1 reduced ADS clipping but did not fix it; all 80
   installed files matched. v0.1.2 passes native validation with zero errors,
   13 format/utility tests, 14 expanded hair fixtures and a 34-object scope audit.
   Six views show no obvious new major attachment failure. These are offline
   results; synthetic poses and BVH counts do not establish runtime success.
2. **Unverified:** v0.1.2 ADS/cutscene behaviour, broad locomotion, crouch,
   floor contact/IK, specific reload/fire/holster, first-person arms, damage and
   alternate routes. Face animation and native hair/cloth collision are absent.
3. **Assembly:** `ch02_0000_body`, `ch02_0020_face`, `ch02_0040_bela_hair`, shared
   `ch02_0201_gpucloth` (dress, hood, inner, sleeves, corset/buttons/catches) and
   their MDF/TEX dependencies. Grace's four boot groups supply current footwear.
   Full source fidelity additionally needs original Bela heels, four omitted
   stitch materials and `ch02_0010_witch _cloak`'s specialized animated shader.
   All source assets are already local. Intentional source cutouts and separate
   mesh/material boundaries are distinct from actual hair/hood intersections.
4. **Rig:** Grace's original 611-bone hierarchy and bind matrices, not a hybrid.
5. **Conversion:** retained joint-direction fitting, target segment lengths and
   0.9 radial scale; file-matrix transpose and +90-degree X rotation adapt to
   Blender Z-up, without rotating the runtime Grace skeleton. Prior dress-only
   pelvis clearance remains at most 25 mm. This revision adds no axis or rest
   correction. It only extends the hood-weight front fade to engine Z=0.150 m
   from 0.075 m (width 0.040 m; nearest-distance fade 0.050-0.075 m). Geometry,
   normals/tangents, UVs and all non-hair weights stay unchanged.
6. **Next risks:** exact ADS lower-lock clearance, cutscene front-lock motion
   under the wider weight transfer, dress deformation and feet/floor contact.
   Residual full-card overlaps remain (8 at rest; maximum 13 in these fixtures).
   Alpha is ignored; some opposite/pitch cases increase from 1 to 6-7 triangles.
   No collision-free claim is made. No obvious new major deformation/attachment
   error was found in the reviewed views. Previous neck, shoulder, elbow, wrist,
   pelvis, knee and ankle checks remain applicable through the exact 34-object
   geometry/non-hair-weight audit; stronger hair poses add new coverage.
7. **Exact changes:** only native mesh payloads
   `natives/stm/character/ch/ch02/0200/20/00/ch0200_20_00.mesh.250925211` and
   `natives/stm/character/ch/ch02/0200/21/00/ch0200_21_00.mesh.250925211` change
   from v0.1.1. Both revised SHA256 values are
   `339bed5b5067b5118abf5823703a327754838643ebad93e9aef5e7118c3a3d4d`.
   The other 78 native files are byte-identical. Exactly four scripts change:
   `headwear_diagnostics.py`, `export_headwear_candidate.py`,
   `audit_headwear_candidate.py` and `assemble_release.py`. Config/README/status
   documents and generated evidence are listed in
   `reports/headwear_v2/changes.json` and `reports/releases/0.1.2/changes.json`.
   Complete v0.1.2 has its own stage; older stages and installed files are intact.

The controlled test package is authorized as a complete standalone release.
Packaging/installation are separate from runtime acceptance. This report
records the pre-package decision, not a successful RE9 test.

