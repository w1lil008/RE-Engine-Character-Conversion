# Current release note — v0.1.3, 10 October 2026

The accepted v0.1.2 hair/hood fix is preserved byte-for-byte in v0.1.3.
The checked source implementation aligns lower forward-lock weights to the
hood, preserving hair geometry and Grace bind matrices. No shoulder bind
transform or hair trimming was introduced here. The user's description of
adjusted shoulder movement is treated as runtime acceptance; the recorded
source correction is the weight sidecar/native export. Fresh 14-pose QA and
six reviewed views are in `reports/stabilization_headwear/`. Older sections
below are investigation history; observation 06 records acceptance.

# Hair/hood corrections — runtime defect remains under investigation

**v0.1.1 tested: reduced clipping, not resolved.** Observation 05 verifies all
80 installed files match v0.1.1. The user's screenshot still shows a blond lower
side lock passing through the outer hood near the shoulder. A second correction
is prepared for a complete v0.1.2 release; it has not been tested in-game.

The first diagnostic used a rear-only rest-coordinate mask, excluding forward
cards, and eight head/chest fixtures without shoulder/arm raises. Its old counts
below remain valid for that limited mask but missed the residual runtime case.
The expanded driver reports both the old mask and **all hair triangles**, and
adds shoulder/arm raises and stronger head turns for 14 synthetic fixtures.

## Second correction and validation

Starting from v0.1.1's native weights, extend the hood-inner transfer fade from
engine Z=0.075 m to 0.150 m, retaining the 0.040 m transition width. The nearest
surface distance fade remains full at 0.050 m and zero at 0.075 m. This includes
lower forward locks previously excluded by the front mask; it changes 2,502
Hair02 and 7,395 Hair01 vertices before quantization. It preserves positions,
topology, UVs, normals/tangents and materials. No hair is deleted or shrunk, and
no new axis/rest-pose correction or collision simulation is added.

The v0.1.1 reference reports are `reports/headwear_v2/native_candidate_*`.
The revised reopened-native reports/renders are `reports/headwear_v2_native/`.
All-card BVH diagnostics (not visible-pixel or collision-free claims):

| Synthetic fixture | v0.1.1 hair triangles implicated | v0.1.2 native candidate |
|---|---:|---:|
| Rest | 8 | 8 |
| Head yaw right | 143 | 12 |
| Aim surrogate | 59 | 10 |
| Arms raised | 147 | 10 |
| Shoulders raised | 257 | 13 |
| Right shoulder | 322 | 12 |

This is not a uniform improvement in every metric: several opposite-turn or
pitch-down fixtures increase from one implicated triangle to six or seven.
Their visible significance remains unclassified; all 14 comparisons are
retained in `reports/headwear_v2/candidate_review.json`.

Six reopened-native front/rear renders show retained front locks without an
obvious new major attachment failure in those views. Residual overlap counts
ignore card alpha; their visible significance is not fully classified. The
fixtures are not captured RE9 ADS animations. The remaining runtime defect is
not declared fixed; the next build exists to test this wider correction.

The native roundtrip preserves all 611 Grace bones/hierarchy/bind matrices and
the exact packed normal/tangent bytes. Both hair variants have SHA256
`339bed5b5067b5118abf5823703a327754838643ebad93e9aef5e7118c3a3d4d`.
`reports/headwear_v2/assembly_scope_audit.json` checks 34 assembled objects:
only two hair objects change weights. Neck/shoulder/elbow/wrist/pelvis/knee/ankle
body and clothing geometry, weights and attachment transforms are unchanged,
so the prior 14 joint-fixture and seam reviews remain applicable. A headwear
cutscene retest is still needed because the locks now follow more hood motion.

Reproduce the second candidate with the pinned portable tools:

```powershell
& ./tools/blender-4.3.2-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python ./scripts/headwear_diagnostics.py -- --candidate --native-input mod/BelaGrace_RE9_0.1.1/natives/stm/character/ch/ch02/0200/20/00/ch0200_20_00.mesh.250925211 --tag headwear_v2 --front-limit 0.15 --front-width 0.04 --render
& 'python' ./scripts/export_headwear_candidate.py --tag headwear_v2
& ./tools/blender-4.3.2-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python ./scripts/headwear_diagnostics.py -- --native-candidate --native-input build/headwear_v2/natives/stm/character/ch/ch02/0200/20/00/ch0200_20_00.mesh.250925211 --tag headwear_v2_native --render
& ./tools/blender-4.3.2-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python ./scripts/audit_headwear_candidate.py -- --tag headwear_v2 --candidate-scene assets/work/headwear_v2_native/BelaGrace_headwear_native_candidate.blend
```

The neutral preview is `assets/work/headwear_v2_native/BelaGrace_headwear_native_candidate.blend`.
Two native candidate files are under `build/headwear_v2/`; the complete release
uses `config/releases/0.1.2.json` and `mod/BelaGrace_RE9_0.1.2/`. No project tool
changes installed files or either older release. Full installation instructions
are in [v0.1.2 README](releases/0.1.2/README.txt).

## First correction — historical v0.1.1 scope

## Finding and correction

`reports/headwear_weight_inspection.json` records source and exported weights.
The two hair materials average about 90–93% `Head_0` weight; the hood averages
42–49%, retaining chest, shoulder and neck influences. `Hair*` influences are
collapsed to the head, while existing torso/shoulder influences remain. Thus
the hair is not wholly rigid on one bone, but no Bela hair/hood collision
simulation is provided. Different skinning is a supported cause of the
reproduced protrusion, not proof of the exact live-game transforms.

The draft transfers barycentric weights from `HoodInner_Mat` onto covered rear
and side hair cards. A smooth blend preserves forward locks toward the face
opening. It changes 1,820 `Hair02_Mat` and 6,088 `Hair01_Mat` vertices before
native byte quantization. No rest-position correction, new bone-axis conversion,
geometry welding, hood reshaping, shader change or physics simulation is added.

Projection/overlap diagnostics use Blender's existing
[BVHTree API](https://docs.blender.org/api/current/mathutils.bvhtree.html).
Overlap counts ignore hair alpha masks and do not automatically establish
visible penetration or collision-free motion. Hair through a solid hood is an
actual defect; separate hair/hood objects and exposed cuff skin are intentional
segmentation.

### Checks on first-correction reopened native files

| Synthetic fixture | Baseline rear-card triangles implicated by BVH overlap | Native candidate |
|---|---:|---:|
| Rest | 1 | 1 |
| Head yaw left | 5 | 1 |
| Head yaw right | 49 | 1 |
| Head pitch up | 1 | 1 |
| Head pitch down | 33 | 1 |
| Aim surrogate | 223 | 1 |
| Opposite aim surrogate | 11 | 1 |
| Neck pitch | 1 | 1 |

The single residual diagnostic has not been classified as visible penetration;
it already occurs at rest. This is not a zero-collision claim. The poses are
synthetic rotations, not captured RE9 ADS animation. Front/rest/aim and rear
rest/aim/opposite-aim renders were reviewed; front locks remain present with no
obvious major new attachment error in those views. Blender shading remains an
approximation of the game materials.

`native_candidate_validation.json` verifies both RE9 hair variants reopen with
611 unchanged Grace bones, hierarchy and bind matrices. Positions, topology,
UVs and packed normal/tangent bytes are unchanged. The exporter retains tangent
handedness from the original native buffer because the upstream parsed reader
discards its fourth component. The largest roundtrip weight error is about
0.0114, from byte quantization. No material/texture files are changed.

`assembly_scope_audit.json` compares all 34 assembly objects: all rest geometry,
topology, UVs, materials and object transforms remain unchanged, as do every
body, clothing, face and boot weight. Only the two hair objects change weights.

## Reproduce with the pinned portable tools

From the project root:

```powershell
& ./tools/blender-4.3.2-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python ./scripts/headwear_diagnostics.py -- --render
& ./tools/blender-4.3.2-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python ./scripts/headwear_diagnostics.py -- --candidate --render
& 'python' ./scripts/export_headwear_candidate.py
& ./tools/blender-4.3.2-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python ./scripts/headwear_diagnostics.py -- --native-candidate --render
& ./tools/blender-4.3.2-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python ./scripts/audit_headwear_candidate.py
```

Separate output scenes are `assets/work/BelaGrace_headwear_candidate.blend` and
`BelaGrace_headwear_native_candidate.blend`; the original preparation scene is
preserved. The sidecar is `assets/work/headwear_candidate_weights.json`.
Diagnostics and renders are under `reports/headwear/`.

Only these draft native files are written under `build/headwear_candidate/`:

- `natives/stm/character/ch/ch02/0200/20/00/ch0200_20_00.mesh.250925211`
- `natives/stm/character/ch/ch02/0200/21/00/ch0200_21_00.mesh.250925211`

They are not a complete mod. Do not copy them into the game while the current
test is underway. Integration into a new full package and an actual ADS/cutscene
retest are the next steps after collecting the remaining baseline results.
Exact project changes are in `reports/headwear/changes.json`.

The first correction was included in the complete standalone v0.1.1 ZIP. Its
80 native files passed validation; observation 05 now supersedes the old
untested state and confirms only a partial runtime improvement. Its separate
draft review and release manifests are retained as historical creation records.

