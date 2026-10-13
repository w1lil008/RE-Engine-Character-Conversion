# v0.2.0 source-animation reconstruction

10 October 2026. The original daughters-family idle has been decoded and
reconstructed on Bela's original RE8 rig. This completes the source-skeletal
reconstruction milestone on `codex/v0.2.0-source-animation`. It does not
complete v0.2.0, a Grace retarget, native RE9 integration or an RE8 runtime comparison.

Subsequent update: the user has visually accepted this source reconstruction.
Milestone B is now implemented separately; see
[offline retarget record](OFFLINE_RETARGET_V0.2.0.md). Its inspection corrects
the preliminary hierarchy assumption below without changing source playback.

The accepted v0.1.2 runtime baseline and v0.1.3 stabilization package remain
unchanged. v0.1.3 installation still needs the user's runtime confirmation.
The protected starting source revision is
`058bea7490e9f6f626de361efe52dda366e0b5d6`. Recovery remains in
`build/checkpoints/accepted_0.1.2/` and `build/checkpoints/v0.1.3_final/`.

## Delivered experiment

Exact input:

```text
assets/extracted/re8/natives/stm/character/ch/animation/ch02_0500/motlist/ch02_0500general.motlist.486
SHA256 e8b9e4319ac382c4017eb4392d1ee722e6eb8da9833cc24ce77b3f080c734478
ch02_0500_General_Idle_Loop
MOTLIST 486 / MOT 458; offset 0x1d0; slot 0; motion 0; switch 0; bank 10
300 frames / 60 FPS; 116 tracked bones; 129 MOT rest bones
```

The resource belongs to the daughters family. Exclusive invocation by Bela
remains unproven. The reconstructed idle shows an upright posture, gentle sway,
small head/neck changes, a clenched left hand and an open right hand. These are
visual observations of the decoded motion. Suitability for Bela's confident
posture is an artistic inference; playable state compatibility is untested.

The primary reproducibility run is under
`build/animation_v0.2.0/source_idle_reproducibility/` (local artifact omitted):

- Original-rig GLB (local artifact omitted).
- Editable Blender scene (local artifact omitted).
- Full 300-frame, 60 FPS, five-second preview (local artifact omitted).
- Textured start (local artifact omitted),
  middle (local artifact omitted) and
  endpoint (local artifact omitted) frames.
- Raw decoded sparse keys, compiled source-sampler matrices, Blender roundtrip
  GLB and concise command logs in the same directory.

The initial corrected scene in `source_idle_validated/` is retained. Its
skeletal/geometry payload matches the primary run; its older JSON duration
metadata used `5` instead of `5.0`, so the whole-file hashes differ. The final
repeat run `source_idle_repeat/` verifies the current exporter separately.
The earlier `source_idle/` diagnostic scene has an unadapted auxiliary cloak
and is not the accepted review artifact.

## Decoder and interpolation

[ReeDecode](../scripts/animation/ReeDecode/Program.cs) reuses pinned ReeLib
through a read-only memory stream. It extracts native translations, XYZW
quaternions, scale channels if present, hashes, parent names, rest transforms,
compression identifiers, sparse frame indices and behavior metadata. It never
calls the native animation writer. Hash/configuration gates select this exact
source resource. The shared rest-table fallback for the optional clip matches
the upstream MOTLIST reader and is scoped to this source list's slot zero.

The idle contains **173 native transform channels and 2,824 decoded keys**:
116 rotation and 57 translation channels. There are no scale tracks in either
selected clip. Generic vector scale sampling exists, but decoding native scale
compression is not empirically certified by these two clips. Constants and
sparse keys are retained in the decoded JSON. The GLB has 258 channels: 173
native channels plus 85 constant MOT-rest fallbacks, not 258 native tracks.

Every encountered idle compression mode was decoded:

| Channel | Native compression | ReeLib mode | Channels |
|---|---|---|---:|
| Rotation | 0x20000 | LoadQuaternions5Bit | 28 |
| Rotation | 0x21000 | LoadQuaternionsXAxis16Bit | 2 |
| Rotation | 0x22000 | LoadQuaternionsYAxis16Bit | 3 |
| Rotation | 0x23000 | LoadQuaternionsZAxis16Bit | 6 |
| Rotation | 0x30000 | LoadQuaternions8Bit | 48 |
| Rotation | 0x40000 | LoadQuaternions10Bit | 12 |
| Rotation | 0x41000 | LoadQuaternionsXAxis | 2 |
| Rotation | 0xc0000 | LoadQuaternions3Component | 15 |
| Translation | 0x00000 | LoadVector3sFull | 27 |
| Translation | 0x20000 | LoadVector3s5BitB | 20 |
| Translation | 0x21000 | LoadVector3sXAxis16Bit | 1 |
| Translation | 0x41000 | LoadVector3sXAxis | 4 |
| Translation | 0x42000 | LoadVector3sYAxis | 5 |

The optional clip also exercises `LoadQuaternions13Bit`, `LoadVector3s10BitB`
and other modes listed in its separate decode report. No general compatibility
claim is made for unexercised ReeLib formats or compression modes.

The pinned source editor replaces individual local components absolutely:
mesh scale is retained, MOT rest T/R supplies the fallback, and authored T/R/S
tracks replace those components. Its sparse sampler uses vector linear
interpolation and normalized quaternion linear interpolation. The project
independently implements that math in Python and compares it against C#
System.Numerics with the editor's actual `FindFrames` method compiled verbatim.
The rest table is not applied as an additive delta onto the mesh bind.

GLB stores baked keys at every native 60 FPS frame, including frame 300 at
five seconds. glTF/Blender use spherical quaternion interpolation between
those keys; the difference from native normalized-linear interpolation is
measured at all half frames. The video contains frames 0–299; the endpoint
remains in the GLB/Blender action for loop-seam inspection.

Unsupported transform flags, unknown compression, missing decoded keys,
unbound bones, duplicate associations, invalid times/quaternions, non-unit
clip blending weights and additional property/vertex animation channels cause
failure. Enemy event metadata is explicitly reported rather than executed.
The selected idle has no property-tree/vertex channels or end clips. Its two
behavior clips include an `app.EnemyTrack` declaration and four normal keys;
the source native file retains their data. This tool does not implement enemy
events, procedural look-at, IK, collisions or animation layering.

## Original rig and rest-pose findings

The original body contains 185 bones; 125 of the 129 MOT bones occur there
with matching parents. Four MOT helpers, `L/R_Foot_Offset` and
`L/R_Hand_Offset`, are added from the source rest table and have no direct
vertex influences. Their runtime IK meaning remains unresolved.
The original body/face/hair/dress union plus those helpers has **368 bones**,
not Grace's 611. All 129 MOT bones and all 116 tracked bones are present.

The actual decoded parents are preserved and evaluated through normal parent
composition. Subsequent inspection confirms `Hip` and leaf `Null_Offset` are
siblings under root; the earlier chain description was incorrect. Source
playback always used the actual parents. Helpers with weighted descendants
still move skin/twist bones. Bone hashes bind the
tracks; bone names establish the inspected mesh correspondence. No mesh-fitting
or transferred v0.1 weights are used.

The 76.162 mm raw MOT-rest/mesh-bind discrepancy is confirmed at `R_Wep`;
root differs by 33.625 mm and some skirt origins by approximately 10–19 mm.
These origins are distinct authoring data, not unexplained unit conversion.
Original mesh inverse binds remain unchanged; the MOT rest fallback and
absolute authored channels define the animated local transforms. All common
component parent definitions agree and world-bind discrepancies are below
0.4 micrometres. Independent skinning checks validate the resulting deformation.

File matrices are transposed from the reader's row-vector representation into
column-vector math. glTF remains Y-up; Blender applies a +90° X rotation to
Z-up. Bone orientation corrections are calibrated only from the original
static binds, then held fixed for every sampled pose. The conversion preserves
scale and original limb proportions.

The preview uses original body, face, Bela hair and GPU-cloth mesh geometry:
131,882 vertices and 209,426 LOD0 triangles, with all eight skin influences
where present. It reproduces skeletal motion of the dress and hood, not RE8
cloth simulation. The auxiliary `witch _cloak` flat effect/rest geometry
obscures the body without its external deformation and is explicitly excluded
from this preview. Its original file and diagnostic export are retained. No
geometry is removed from either v0.1 package. Engine shader helper geometry
also affects full-scene bounds; finite bounds alone are not an anatomical test.

The header references `Character/CharacterExtraAnimation.jmap`; its exact
runtime resolution and procedural effects are not established here. The
source-editor skeletal sampling path does not require that resource. This
does not prove that the game applies no extra constraints.

## Validation evidence and practical limits

| Check | Result | Evidence |
|---|---|---|
| Raw MOT headers, native flags, key counts and sparse frame indices | Match decoded values | `tests/test_source_animation.py` |
| Quaternion norms | Maximum deviation 8.28e-8 | Decoded source values |
| Independent Python vs pinned editor C# world transforms | 601 samples at 120 FPS; maximum matrix component error 8.50e-7 | `source_idle_decode.json` |
| Blender vs original-source world transforms | 601 samples; maximum joint error 0.962 micrometres | `source_idle_blender.json` |
| Blender export/reimport vs original-source transforms | 601 samples; maximum joint error 1.191 micrometres | `source_idle_roundtrip.json` |
| CPU eight-influence skinning vs Blender evaluated geometry | Every triangle corner at five poses; maximum error 0.913 micrometres | Skinning report |
| Loop endpoints | Largest source joint difference 0.700 mm; largest rotation difference about 0.122° | Decode/phase reports |
| Complete preview | H.264, 300 samples, five seconds, constant 60 FPS | MP4 `stts`, `stsz`, `mdhd` tables |
| Baseline protection | 815 original local inputs, 160 staged native files across two releases and both ZIP hashes unchanged | Baseline/workflow reports |

The loop seam is present in the source sampling, with the largest position
difference at `skirt_5_6`. It was not silently smoothed. The native root's
endpoint difference is below one micrometre. A later runtime loop should
preserve authored timing and evaluate entry/exit blending explicitly.

The numeric comparison is against **headless source-editor sampling code**,
not a running graphical REE Content Editor or an RE8 game session. ReeLib is
the shared decoder on both sides, so these tests independently validate
sampling, hierarchy, coordinate conversion, export and skinning; they are not
an independent reverse-engineering proof of every decompression formula.
Original RE8 runtime/graphical-tool comparison remains useful before runtime
integration. No new RE9 runtime functionality is claimed.

Textured stills use approximate glTF materials. The full video uses inexpensive
solid material shading to review all motion frames. Native cloth, hair physics,
blendshapes, facial expression/lip-sync, look-at, IK and event processing are
absent. Both source faces contain blendshape sections, but the pinned mesh
reader's blendshape import is disabled/broken. Body decoding establishes no
blink compatibility; the accepted converted face remains unchanged.

Structured results and artifact hashes are collected in
phase results (local artifact omitted). Detailed reports
remain under `reports/animation_dev/`; large binaries and render logs stay local.

## Optional original gesture

The actual source name is
`ch02_0500_General_Emotion_Eldest_Provocative`, with the `General` segment.
Same resource hash; offset `0xc20b0`, slot 10, motion 200, switch 0, bank 10;
222 frames / 60 FPS; 111 bone tracks; inherited 129-bone rest table.
It has 168 native channels and 14,790 keys. The reconstructed motion moves
forward while lifting clenched hands and bending the elbows. Its root endpoint
travels **3.370 m** in **3.7 seconds**; it is not a neutral looping idle.

Following-camera Blender scene (local artifact omitted),
222-frame video (local artifact omitted) and
middle review frame (local artifact omitted)
retain the original bone keys and root motion. Only the camera and lights follow
the root. Its GLB remains `source_provocative/source_idle.glb`, the common
workflow artifact filename; the internal animation name is the original clip.

The optional clip passes 445 Blender/source comparisons and 445 reimport
comparisons, with maximum joint error about 0.0184 mm after reimport.
It is a future gesture/upper-body research candidate. Its authored forward
motion, fist controls and lower-body transitions require review before any
masking or playable use. No compatibility with Grace's weapon layers is proven.
Idle Emotion v4/v5 and Appearance were not decoded in this phase.

## Reproduction

Production tool pins remain in `config/toolchain.lock.json`. This experiment
adds `config/source_animation_toolchain.lock.json` and a locked NuGet graph.
ReeLib is at `ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef`; REE Content Editor at
`cedd2f421b476ac50fbeb271bc71fdd3f2b2bb1c`. Their tracked files must be clean.
The actual sampler and inspected reader files are hash-checked before build.

Portable .NET SDK 10.0.401 compiles the pinned library's modern C# syntax.
Portable SDK/runtime 8.0.425 runs its net8 output. Both SDK archives were
verified against Microsoft's SHA512 metadata and extracted under `tools/`;
no system SDK is required. A fresh machine needs those pinned archives,
exact Git checkouts in `tools/research/`, portable Blender 4.3.2, project Python
dependencies, owned RE8/RE9 extracts, cached texture previews and the protected
v0.1 checkpoint/manifests. Download URLs and hashes are in the lock files.
NuGet restore uses the checked lock graph and an explicit official source.

From the project root in PowerShell:

```powershell
$projectPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $projectPython scripts/source_animation_workflow.py --output build/animation_v0.2.0/idle_new_run --report-name idle_new_run --video
& $projectPython -m unittest discover -s tests -v
& $projectPython scripts/source_animation_mapping.py
```

Use a fresh output directory: previous reconstruction evidence is protected
from overwrite. The workflow checks baseline hashes before and after decoding,
GLB export, Blender validation/rendering, export/reimport and geometry skinning.
Tests that require local reconstruction data explicitly skip if it is absent;
this phase's actual run has zero skips.

For the optional clip use `--config config/source_provocative_v0.2.0.json` and
a new output/report name. After its normal workflow, render a following review
camera using `source_animation_review.py` with the same `--output`,
`--report-name` and `--video` arguments through Blender's `--python` interface.
This post-processing has no armature-edit path.

Primary tool sources: [ReeLib MOT reader](https://github.com/kagenocookie/RE-Engine-Lib/blob/ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef/REE-Lib/RszFile/MotFile.cs),
[source-editor animator](https://github.com/kagenocookie/REE-Content-Editor/blob/cedd2f421b476ac50fbeb271bc71fdd3f2b2bb1c/ContentEditor.App/Graphics/Animator.cs),
[animation-tool documentation](https://github.com/kagenocookie/REE-Content-Editor/wiki/Animation-tools).

## Preliminary Grace mapping and next milestone

Mapping measurements (local artifact omitted)
and [read-only mapping utility](../scripts/source_animation_mapping.py) identify
24 core correspondences against the unchanged 611-bone Grace bind. The plan
is measured and reviewed structurally, but no animated transform mapping has
yet passed validation:

| Source | Grace target | Policy |
|---|---|---|
| root, Hip, Spine_0/1/2, Neck_0/1 | Same names | Compose source helper chain; preserve target offsets |
| Head | Head_0 | Calibrate rest bases before copying motion |
| L/R_Shoulder | L/R_Arm_Clavicle | Preserve clavicle/upper-arm proportions |
| L/R_UpperArm, Forearm, Hand | L/R_Arm_Upper, Arm_Lower, Arm_Hand | Retarget rotations; retain weapon/finger layers |
| L/R_Thigh, Shin, Foot, Toe | L/R_Leg_Upper, Leg_Lower, Leg_Foot, Leg_Toes | Preserve lengths; inspect foot contact |

Source and target local axes, bind origins and parents differ. Direct name
substitution or the mesh-fitting weight mapper is not an animation retargeter.
Source `Null_Offset` has no direct counterpart: compose its transform with
source root before mapping the pelvis chain. Hand/foot offsets, twist/muscle
bones, dress controls and native layer masks remain unresolved. Keep Grace's
weapon attachment, fingers, aiming, recoil, reload and interaction controls.

The exact next experiment is an **offline original-idle retarget onto the
existing 611-bone Grace rig**: first prove the 24 measured rest-basis mappings
with zero motion and one known-axis rotation per limb. Zero source delta must
leave the target bind exactly unchanged; child offsets must preserve target
limb lengths. Then apply only the decoded body rotation deltas, compose the
root/helper chain, retain target translations initially, and separately test
in-place pelvis sway and foot contacts. Export a separate review GLB/Blender
scene beside the original clip. Check head/shoulders, elbows, wrists, hips,
knees, foot sliding, loop seam, accepted garments and attachment points.
Keep fingers/weapon controls untouched in that first body experiment.

| Workstream | Complexity | Next dependency |
|---|---|---|
| Exact source decode/export | Medium; completed | Existing supported ReeLib compression and validated hierarchy |
| Core offline retarget | High | Rest-axis calibration, helper composition, target limb lengths |
| Root/foot contact and transitions | High | In-place/root policy and measured offline playback |
| Twist, garment and layer masks | Research-dependent | Grace native contracts and layered animation binding |
| Native RE9 integration | Research-dependent | Separate authorization and target format/binding proof |
| Face/blinking/expressions | Research-dependent | Facial control mapping and working morph decoding |

Source reconstruction passes the offline skeletal acceptance gate. No essential
encountered compression mode remains unsupported. Graphical/game comparison,
procedural motion and controller behavior remain explicitly outside that gate.
No further source file is needed for the first offline core-body experiment;
exact runtime masks/IK contracts and a reference RE8 playback are needed before
claiming fidelity to complete in-game behavior. Native RE9 writing, controller
changes and installation remain outside this authorization.

