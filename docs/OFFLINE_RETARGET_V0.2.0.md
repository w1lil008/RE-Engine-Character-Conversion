# v0.2.0 Milestone B: offline idle retarget

The approved RE8 daughters idle now plays on the accepted Grace-based Bela
model using its original **611-bone hierarchy**. The offline retarget passes
mathematical, geometry, Blender and export/reimport checks and is **ready for
the user's visual review**. It has not been accepted by the user or tested in
RE9. No native animation writer, controller edit or installation is included.

Development remains on `codex/v0.2.0-source-animation`. The visually approved
source at checkpoint `44eb9e1` is an immutable reference: all nine primary
artifact hashes are checked before and after development. The user's visual
acceptance is recorded in
source reference acceptance (local artifact omitted).
The previous source-phase engineering report remains a historical milestone;
the hierarchy and mapping corrections below supersede its preliminary plan.

## Review artifacts

Everything for the final primary experiment is under
`build/animation_v0.2.0/retarget_idle/`:

- retarget_idle.blend (local artifact omitted): editable target character/action.
- retarget_idle.glb (local artifact omitted): importable target model, original skin/binds and body animation.
- retarget_idle_60fps.mp4 (local artifact omitted): full 300-frame, five-second animation.
- comparison.blend (local artifact omitted) and
  comparison_60fps.mp4 (local artifact omitted):
  approved RE8 reference on the **left**, retarget on the **right**.
- Matching textured start/middle/endpoint images in `comparison_*.png` and
  `three_quarter_*.png`; extra `side_*.png`, `head_shoulders_*.png` and
  `feet_*.png` inspection angles. The endpoint is frame 300 at five seconds;
  videos use frames 0–299 to avoid duplicating the loop endpoint.
- `retarget_idle_roundtrip.glb`, `retarget_matrices.npz`, `target_rig.json` and
  `retarget_config.json`: reimport and mathematical evidence.

The comparison uses one shared camera and synchronized 60 FPS timing. Scene
placement alone separates the models horizontally. Both retain their real
proportions; the target is shorter. Engine shaders are approximated for offline
preview. Textured stills use EEVEE; full videos use material-coloured Workbench
shading. The floor is a review guide and is excluded from the target GLB.

The independent fresh build is `build/animation_v0.2.0/retarget_idle_repeat/`.
Its target GLB is byte-identical. `retarget_idle_initial/` is retained as an
earlier diagnostic before floor placement/comparison framing improvements.

The optional original gesture preview already exists:
Provocative, original movement preserved (local artifact omitted).
Its 222 frames/60 FPS and 3.37 m forward root travel are unchanged. It is not
retargeted or forced into an idle during this milestone.

## Mapping corrections and coordinate method

The preliminary 24 correspondences were checked against the actual native
target and the approved source's mesh binds, MOT rest table and decoded tracks.
Two corrections are material:

1. **Hip and Null_Offset are sibling children of root.** Null_Offset is a leaf
   in the inspected source hierarchy, without skin/descendant influence on
   the body. The earlier `root → Null_Offset → Hip` description was wrong.
   The approved source playback had always evaluated the actual decoded
   parents correctly; its animation is unchanged. Composing Null_Offset into
   Hip here would introduce an incorrect extra transform.
2. **RE8 Foot maps to Grace Leg_Ankle.** Grace's chain is Upper → Lower →
   Ankle → Foot → Toes. The additional Leg_Foot retains its local bind;
   Toes receives the source Toe rotation through the actual target parent.

| Source | Target |
|---|---|
| root, Hip, Spine_0/1/2, Neck_0/1 | Same names |
| Head | Head_0 |
| L/R_Shoulder | L/R_Arm_Clavicle |
| L/R_UpperArm, Forearm, Hand | L/R_Arm_Upper, Arm_Lower, Arm_Hand |
| L/R_Thigh, Shin, Foot, Toe | L/R_Leg_Upper, Leg_Lower, Leg_Ankle, Leg_Toes |

The original mesh bind and MOT rest remain separate. Native channels are
sampled exactly as in the accepted reconstruction: MOT rest fallback and
absolute local channel replacement, followed by actual source hierarchy
composition. The original mesh bind defines the skin reference and rotation
bases. The two are not substituted for one another: several source rest
rotations differ substantially from the mesh bind.

In column-vector world-space rotation notation:

```text
Dsource(t) = Rsource(t) * transpose(Rsource_mesh_bind)
Rtarget_desired(t) = Dsource(t) * Asegment * Rtarget_bind
Rtarget_local(t) = transpose(Rtarget_parent(t)) * Rtarget_desired(t)
```

`Asegment` is a proper shortest swing rotation aligning the target bind segment
direction to the corresponding original source bind segment. It is constant
and is independently verified using actual child origins. This compensates
different neutral arm/leg/spine directions while preserving the target bone's
roll convention. It is identity for the root, pelvis, head, wrist and toe
orientations where that segment calibration is not used. All resulting
rotations are encoded as normalized XYZW quaternions with sign continuity.

With alignment disabled, zero source rotation delta preserves the target bind
orientation. With alignment enabled, zero delta produces a **calibrated pose**
whose segment directions match the source. This calibration is animation;
neither the target bind matrices nor skin weights are changed. Known-axis
tests verify that arbitrary source world rotations survive the differing
native bone rolls. This algorithm does not use the mesh-fitting weight mapper.

All target non-root local translations/scales remain fixed. Source root sway
is retained relative to frame zero, without scaling or foot-lock manipulation.
A constant **−7.173 mm vertical root placement** puts the actual accepted boot
sole contact patch on the review floor at frame zero. It does not change the
relative root trajectory or any limb offset. The original root's starting
horizontal position is recentered for the isolated target scene.

## Controls, geometry and source-track scope

All 611 bones, parents and original bind/inverse matrices are retained.
The six base-outfit native parts are read directly from v0.1.3: upper, lower,
both hands, face and hair. Alternative upper/hair native files are installation
variants, not additional geometry to stack into this scene. The scene contains
the complete base assembly, with 214,120 triangles in those native components.

Every exported position, triangle index, weight and positive weighted-bone
association is checked against the accepted native input. Eight influences
are retained where present. Hair/hood follow and dress/thigh-clearance sidecars
and native payload hashes remain identical. No geometry or weight adjustment
was made, including no hair trimming.

The body layer has 24 rotation channels and one root translation channel,
baked at 60 FPS with 301 samples including the endpoint. All **587 unmapped
local transforms** are unchanged. Fingers, weapon attachment/recoil controls,
IK controls, face and other native helpers inherit through their existing
parents without new local keys. Twist/muscle branches retain their original
local binds; no runtime constraint system is reproduced here.

All 116 source tracks have an explicit disposition in
export/mapping report (local artifact omitted).
Body rotation is transferred; non-root translation is intentionally retained
from the target. Source fingers/weapons are excluded from this body layer,
hair/garment tracks lack a corresponding target control contract, and source
IK offsets are not imposed on Grace. Unknown tracks fail rather than vanish.
The original keys remain in the protected reference. This is a complete
five-second **body retarget**, not a conversion of every source subsystem.

## Validation and residual issues

| Verification | Result |
|---|---|
| Automated suite | 39 tests, zero failures/errors/skips |
| Source/target segment directions | Maximum error about 0.000003° over 601 poses |
| Quaternion normalization | Maximum GLB deviation 5.96e-8 |
| Non-root local translations/bone lengths | Zero change |
| Unmapped controls | All 587 local matrices unchanged |
| GLB vs mathematical retarget | Maximum world matrix component error about 2.02e-7 |
| Blender and full 611-bone hierarchy | 601 integer/half-frame comparisons pass |
| Blender export/reimport | Maximum joint error approximately 1.80 micrometres |
| Geometry skinning | All triangle corners at five poses; maximum error approximately 0.97 micrometres |
| Loop seam | Maximum target joint difference 0.564 mm; maximum rotation difference 0.123° |
| Video completeness | Both MP4s have 300 H.264 samples, constant 60 FPS, five seconds |
| Reproduction | Fresh target GLB is byte-identical |
| Protection | Nine accepted source artifacts, 815 original inputs, 160 staged natives and both v0.1 ZIPs unchanged |

Root sway spans **47.566 mm X and 12.686 mm Z**, with effectively no net loop
travel. The root's endpoint difference is below one micrometre. This is authored
idle sway, not accidental accumulated locomotion.

Foot horizontal range is approximately **5.1–5.8 mm** across the retarget,
versus **2.6–3.6 mm** across the approved source. Maximum target movement away
from the first pose is approximately 4.5 mm. The target upper legs are 95.24%
and lower legs 97.37% of their source bind lengths; retained hip/limb offsets
also differ. Exact segment directions plus unchanged target lengths explain
the additional small positional movement under unscaled source root sway.
No hidden IK or root-sway attenuation was used to force planted feet.

At the five measured geometry poses, the bottom boot contact patch reaches
about **0.75 mm below** the review plane at its lowest. Its vertices span a
few millimetres of height due to sole shape and ankle motion. This is recorded
as a residual for inspection, not a collision/foot-lock proof. Runtime IK
remains an independent future integration check.

The target preserves Grace's neutral finger locals. Therefore the source's
clenched left fist is absent and the hands differ visibly. The character also
has the accepted shorter proportions and Grace footwear. Those differences
are deliberate consequences of protecting playable controls and geometry.

The lower dress shows **rigid folds and an uneven hem** under the staggered
stance. Large relative edge strain occurs on some very short bind edges:
examples around 0.4–1.2 mm become roughly 27–34 mm in the initial posed lower
garment. Those are local skin-deformation limitations of the preserved garment
weights, not quaternion/skeleton errors. They are not concealed by a geometry
edit or simulation. Subsequent lower-dress edge motion is small (at midpoint,
99th percentile length ratio about 1.027 relative to frame zero, with maximum
edge-length changes below 0.6 mm for the two lower materials). Hood/sleeve
strain is also recorded, and the head/shoulder stills show the accepted hood
and hair moving with the retargeted torso/head. Visual acceptance of these
folds and hood behavior belongs to the user.

No major limb twisting, detached body section or unstable loop appeared in the
reviewed start/middle/end/side/head/foot images. Finite transforms and skinning
agreement do not prove collision-free garment motion. Native materials/lighting,
weapon IK, controller blends and RE9 animation acceptance remain untested.
Facial animation, blinking, lip-sync and native cloth physics are outside this
phase. Original costume separations between sleeves/gloves remain intentional.

Machine-readable evidence and complete local artifact hashes:
phase results (local artifact omitted),
numerical validation (local artifact omitted),
skinning/contact/strain (local artifact omitted).

## Reproduction and review gate

Use the existing pinned Python, Blender 4.3.2, accepted native inputs and
approved source artifacts. No source decoding/re-export is performed by this
workflow, preserving the approved source reference unchanged.

```powershell
$projectPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $projectPython scripts/retarget_idle_workflow.py --output build/animation_v0.2.0/retarget_new_review --report-name retarget_new_review --video
& $projectPython -m unittest discover -s tests -v
```

Outputs must be fresh directories. Read-only native hash gates run before and
after. The workflow exports, validates Blender playback, renders complete
comparison/target previews, reimports Blender's export, measures motion and
checks independent geometry skinning. Code/configuration and structured reports
are versioned; game-derived binaries and rendered media remain local.

For manual acceptance, watch both complete previews and inspect the extra
angles for head/neck, hood/hair, sleeves/wrists, hips, dress/hem and feet.
Confirm that the preserved hand differences and residual lower-dress folds
are acceptable for this prototype. Review the loop boundary through repeated
playback. This review promotes only the offline retarget, not a runtime mod.

After the user's acceptance and authorization, **Milestone C** is native RE9
resource conversion: establish a lossless/validated writer for MOT **983** and
MOTLIST **1047**, preserve bone hashes, native rest/binding semantics, sparse
timing/compression and body-layer masks, and prove read/write/read sampling
equivalence before any game installation. Identify one isolated target idle
reference and its bank/state binding plus blend/IK contract. A separate
reversible runtime experiment follows that native-resource proof. Grace's
weapon, interaction, aiming and traversal systems stay protected. No part of
Milestone C is implemented in this task.

