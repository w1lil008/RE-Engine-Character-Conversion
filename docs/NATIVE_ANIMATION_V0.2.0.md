# Milestone C — native animation encoding and validation

The user accepted the Milestone B retarget at `e579c25`. Its source, outputs,
611-bone rig, geometry, weights and corrections remain protected by SHA256.
This milestone produces **parser-validated native development resources**.
Nothing was installed, registered, activated or tested in RE9. Runtime
compatibility and state binding are the next gate, not inferred from parsing.

## Outputs

Primary: `build/animation_v0.2.0/native_idle_canonical/`.

| File | Purpose |
|---|---|
| `native/bela_idle.mot.983` | Standalone five-second body animation |
| `native/bela_idle.motlist.1047` | One-entry, unregistered prototype list |
| `reimport_report.json` | Independent reader and 611-bone sampled comparison |
| `metadata_dispositions.json` | Explicit rest, track, event and descriptor policies |
| `workflow_report.json` | Protected inputs and encoding verification |

Independent fresh run: `build/animation_v0.2.0/native_idle_canonical_repeat/`. Its two
native resources are byte-identical to the primary outputs. The repeat run
also records the actual original-idle decoded-float roundtrip described below.
Current consolidated evidence is in `reports/native_animation_v0.2.0/`.
The review package is `dist/BelaGrace_NativeAnimation_0.2.0_MilestoneC.zip`.
It contains resources and review documents, with no install paths, bank file,
controller, auto-installer or Fluffy activation metadata. Original Grace
animations, decoded source assets and large diagnostics are excluded.

## Untouched RE9 roundtrip evidence

Original source: `assets/extracted/re9/natives/stm/animation/ch/ch02/ch0200/motlist/ch0200_generalm.motlist.1047`.

SHA256: `41e875ab1fb08a4347dad2f4d3ea296de2cf1b7e0df205161057d457eaddcf20`.
It contains 270 slots referring to 211 unique MOT 983 resources, including
aliases and empty slots. All 14,207 bone tracks, 16,495 channels and 547,472
decoded keys are retained in the preservation test.

Two complementary roundtrips are verified:

1. **Actual decoded-float encode on an unchanged original Grace idle.** Slot
   zero is extracted without changing its bytes, decoded by pinned ReeLib,
   written by its native MOT writer, then decoded in another process. All
   tracks, compression modes, flags, timestamps, header metadata, joint-map
   reference and decoded behavior metadata compare identically. Eleven float
   components change by at most **2.0e-9** through recompression, below the
   1e-6 component tolerance. The input motion is not edited or retargeted.
2. **Complete list preservation roundtrip.** The list is decoded into typed
   control records and a complete ordered partition of packed/opaque data,
   serialized to JSON, encoded again, and independently decoded by ReeLib.
   The result is byte-identical and the complete decoded documents match.
   This protects unknown words, compression codes, event data, references,
   padding, aliases and unrelated clips as well as recognized fields.

The second method deliberately preserves original compression codes rather
than reconstructing them from floating-point values. Opaque event/property
partitions are retained, not presented as fully understood authoring schemas.
It is a lossless preservation workflow, not a general animation editor.

The upstream whole-list rewrite was tested separately and rejected as the
preservation path: it normalizes nine original bone-count headers and changes
some compressed values. It is retained only as diagnostic evidence. The
single original idle's own 70-bone table avoids this count normalization issue.

## Encoding the accepted motion

No new retargeting or fitting occurs. The encoder reads all **25 accepted GLB
channels**: rotations on 24 body bones and translation on `root`, each with
301 samples at frames 0–300, 60 FPS. Absolute bone-local transformations and
the accepted rest/hierarchy corrections are copied explicitly.

The native list's original motion table contains 70 bones, not the mesh rig's
611. All 24 animated body names are present. The 58 table bones also present
in the mesh have matching direct parents; their rest translations and
rotations are encoded from the approved target bind. Twelve animation-only
helpers retain their original native rest information. Their names include
weapon, camera, ground and IK targets absent from the mesh's 611-bone table.
They receive no new animation channels. Their live bindings remain unknown.

The native MOT table is an animation binding table; it does not replace the
character's runtime skeleton. Offline validation applies its supported body
bindings to a copy of the existing 611-bone target. Every other target local
remains at its accepted bind, subject only to native float32 rounding for the
shared rest entries. Weapon/finger/IK controllers are not authored or changed.

Translations use uncompressed float32 XYZ. Rotations use the native reader's
uncompressed modes: **22 XYZ tracks (`0xC0000`) and two XYZW tracks (`0x00000`)**.
Frame indices are signed 16-bit integers. Both formats are decoded separately
by the strict Python reader and pinned C# ReeLib reader.

Header sizing follows the upstream writer: standalone `motSize` ends at the
motion data/name, excluding the aligned rest table. The first embedded list
entry stores zero as its shared-table marker. Standalone and embedded animation
data compare identically after accounting for this explicit header convention.

XYZ is observed throughout the original RE9 list. It reconstructs positive W
as `sqrt(max(0, 1-x*x-y*y-z*z))`. A trial encoding every rotation as XYZ produced
**0.257 mm** maximum joint error near half turns and failed our 0.05 mm
precision gate. `R_Arm_Clavicle` and `L_Leg_Upper` therefore store all four
components. Full XYZW preserves the accepted continuous signs, including the
left thigh's W crossing zero. Stable XYZ tracks canonicalize equivalent signs.

**Compatibility risk:** full XYZW is supported by the pinned MOT 983 parser
but was not found among the 211 original GeneralM clips. Actual RE9 support is
unverified. ReeLib's version-changing writer also automatically selects XYZ
for full quaternion tracks, so re-saving the prototype through that writer
would lose this precision policy. Use the tested project encoder. This is a
specific runtime format gate, not a claim that a successful parse proves loading.

## Root, metadata and event policies

The root channel is copied unchanged from the approved retarget. It contains
periodic sway: **47.566 mm X range and 12.686 mm Z range**, a constant
**−7.173 mm Y floor offset**, and approximately **0.909 micrometres net loop
translation**. No accumulated locomotion, additional trajectory or new root
channel was introduced. Suppressing that accepted periodic sway would change
the approved motion. How RE9 applies root translation to the actor must still
be checked separately from the rendered skeleton.

The fresh one-entry list retains slot zero's motion ID 0, switch 0, mask ID 0,
tag 0, type 1, zero flags/physics flags and **all 12 unknown index words**.
These are local prototype descriptors; no default-idle or live-state binding
is claimed. Mask ID zero is not assumed to mean a verified full-body mask.
Original list/base-list/motpack relationships are recorded in the untouched
roundtrip. The new list has no base-list or motpack dependency and no bank.

The original idle references
`GameAssets/Character/CharacterPrefab/cp_A1/cp_A100/JointMap/cp_A1JointMap_ForConvert.jmap`.
That reference is retained; the resource's runtime remapping behavior is not
yet verified. There are no new GPU motion, scale channels, property trees,
properties or behavior events in the body-only prototype.

Original Grace events are **preserved in the original resource and roundtrip**,
not silently removed from an existing state. The fresh prototype intentionally
does not transplant that state's events. Its original CLIP 90 metadata has a
30-frame timeline, five tracks, twelve properties and multiple key classes.
Tracks include look-at blend, upper-action cancel/end and body breathing.
Their invocation and timing would require a controller-aware integration
decision; copying them into the new five-second state is not justified.

## Reimport and preservation results

Across **601 poses at 120 FPS**, all 611 joints are compared with the accepted
Blender/GLB motion, including every key and midpoint:

| Measure | Result |
|---|---:|
| Maximum joint-position difference | **0.144 micrometres** |
| Maximum world rotation difference | **0.0000425°** |
| Python versus ReeLib key-component difference | **2.98e-8** |
| Maximum quaternion norm error | **6.67e-8** |
| Minimum signed adjacent quaternion dot | **0.9999978** |
| Non-root translation / bone-length change | **0** |
| Unmapped target local matrix rounding | **4.34e-8** |
| Maximum joint loop endpoint difference | **0.564 mm**, consistent with accepted source |
| Maximum rotation loop endpoint difference | **0.122°** |

Rotation error is measured after projecting float-rounded bind bases onto
SO(3), avoiding false angular error from tiny scale residuals. NLERP as used
by the pinned viewer is compared against the approved GLB's SLERP at midpoints;
actual game interpolation remains a runtime question. Foot horizontal ranges
remain approximately **5.1–5.8 mm**, as accepted by the user.

Original geometry, inverse binds, weights, hood-follow correction and thigh
clearance are not rewritten. Protected checks cover 57 Milestone B artifacts
and source/manifest files, nine original-source reference artifacts, 815
original local inputs, 160 v0.1.2/v0.1.3 native files and both release ZIPs.
The consolidated test report records the current full-suite results.

## Bank and controller findings

Read-only fresh MOTBANK parsing confirms Grace's main bank references
GeneralM as bank ID **0**, GeneralM_Add as **2000**, GeneralH as **100**,
Emote as **50**, and additional motion-tree and weapon-specific lists. Bank
type/mask conditions participate in selection. A bank ID by itself is ambiguous.

GeneralM slot zero is `ch0200_GeneralM_0000_Idle_caution` (Motion ID 0, switch
0, **814 frames**). Slot one is `ch0200_GeneralM_0001_Idle_Loop_VerB` (ID 1,
switch 0, **one frame**). Other idle, additive, lighting, crouch and transition
clips exist. Neither label proves which idle the current Grace state invokes.

Nine original FPS/TPS MOTFSM2 45 resources were extracted to a new development
directory from official archives opened read-only. Their **577 transition
records** and reference maps decode with bounded checks. Records expose timing,
interpolation and continuation layer/mask fields; all extracted continuation
layer/mask pairs are zero. This does not establish node-level joint masks.
BHVT node actions and embedded RSZ state selection were not decoded. No live
REFramework dump was taken and no runtime inspection script was installed.
Full evidence, extraction provenance and unresolved dependencies are in
`reports/native_animation_v0.2.0/binding_analysis.json`.

## First isolated runtime experiment — proposal only

After explicit authorization, begin Milestone D with a **read-only capture in
one stationary, unarmed Grace gameplay state**. Record the actual character
Motion component, runtime joint hashes (including the twelve helpers), active
layers, bank resources/type/mask, bank ID, motion ID, switch, frame, joint-map
and mask selection, and actor/world transform for ten seconds. Repeat while
aiming and returning to idle to identify the boundary with weapon layers.
Discover the methods from that RE9 build's SDK; no unverified API names or
hard-coded bank IDs are prerequisites of this proposal.

The first activation experiment should then load the **new, separate prototype
list** into a temporary bank/layer or isolated viewer supported by the observed
runtime API, with the captured body mask and a verified unused bank identity.
Keep original banks and controllers registered unchanged. First prove that
MOT 983 accepts the two full XYZW tracks and binds the 24 body bones; then play
exactly one five-second cycle without transitions, combat or event copying.
Capture head/shoulders/hood, pelvis/dress, feet and actor transform. Compare
the loaded animation with the accepted Blender reference and ensure no actor
translation accumulates. Stop immediately on bad binding, parsing, pose or IK.

Disable the experiment by removing its optional development loader and
temporary resources and restarting the game. The existing character package,
official archives, saved controllers and saves remain untouched. Do not
overwrite GeneralM's idle or assign its ID based on a filename. If temporary
loading cannot be verified, stop and document that integration blocker before
any activation. Transitions, aiming/reload/interaction/cutscene tests follow
only after the isolated clip is accepted.

## Reproduction and remaining limits

Use the pinned SDKs and ReeLib checkout already locked by the source phase:

```powershell
& $projectPython scripts/native_idle_workflow.py --output build/animation_v0.2.0/native_idle_new_run
& $projectPython -m unittest discover -s tests -v
& $projectPython scripts/native_idle_finalize.py
```

`$projectPython` is the project's existing Python executable. The workflow
requires a fresh build directory, verifies protected inputs and pinned tools,
performs both original roundtrips before encoding, independently reopens MOT
and MOTLIST, compares all poses, and re-encodes to check repeatability.

The encoder is scoped to this body-only resource, with all accepted channels
accounted for. It does not author arbitrary event tracks, convert controllers,
register banks, implement blinking/cloth, modify rigs or promise support for
all compressed MOT formats. The generic original-list writer is not used for
replacement distribution. Main risks are full-quaternion engine support,
joint-map/helper semantics, live bank selection, root extraction, state events,
IK and body/weapon layering. Each requires Milestone D evidence.

Pinned primary sources:
[MOT reader/writer](https://github.com/kagenocookie/RE-Engine-Lib/blob/ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef/REE-Lib/RszFile/MotFile.cs),
[MOTLIST](https://github.com/kagenocookie/RE-Engine-Lib/blob/ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef/REE-Lib/RszFile/MotlistFile.cs),
[MOTBANK](https://github.com/kagenocookie/RE-Engine-Lib/blob/ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef/REE-Lib/RszFile/MotbankFile.cs),
[MOTFSM2](https://github.com/kagenocookie/RE-Engine-Lib/blob/ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef/REE-Lib/RszFile/Motfsm2File.cs).
These sources were inspected locally at the pinned revision. Parser support
and observed extracted data are distinguished from untested engine behavior.

