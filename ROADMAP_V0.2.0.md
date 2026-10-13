# Bela RE8 → RE9: v0.2.0 animation conversion roadmap

Research snapshot: **10 October 2026**, preserved below. The subsequent
authorized source-animation phase has now completed the original idle's
skeletal decoding, GLB/Blender playback, source-editor sampling comparison,
geometry validation and reimport checks. See
[implementation evidence](docs/ANIMATION_SOURCE_V0.2.0.md) and
phase results (local artifact omitted). Milestone B has
completed the first offline Grace retarget as well. The user has visually
accepted source checkpoint `44eb9e1` and retarget checkpoint `e579c25`.
See [Milestone B evidence](docs/OFFLINE_RETARGET_V0.2.0.md). Milestone C now
implements a tested body-only native encoder, original-animation roundtrips
and independent reimport validation. See
[native engineering evidence](docs/NATIVE_ANIMATION_V0.2.0.md). Native resources
remain unregistered development artifacts; runtime format support and live
state binding await separately authorized Milestone D testing. Inventory entries
and hypotheses below describe
the original research snapshot; the implementation record supersedes its
pending source-decoding/visualisation statements for the two decoded clips.

Authorized Milestone D Stage 1 now prepares read-only runtime instrumentation,
independent joint-map inspection and a reversible first-playback experiment.
Live binding evidence still requires a manual Grace gameplay capture; no new
animation has been activated. See [runtime preparation record](docs/RUNTIME_ANIMATION_STAGE1_V0.2.0.md).

Evidence labels used throughout:

- **Verified locally:** current files were read, measured or rebuilt here.
- **User-tested:** the user reports a successful RE9 test; the recorded scope
  applies, not every possible scene or action.
- **Upstream documented:** a primary tool source describes a capability; it
  has not passed this project's exact cross-game runtime experiment.
- **Proposed / unknown:** a design to test or a missing fact, not compatibility.

## 1. Technical project summary and protected starting point

v0.1.3 is a standalone stabilization patch. Its 8 meshes, 31 MDF variants and
41 textures are byte-identical to accepted v0.1.2. The complete 80-file native
rebuild passes. Grace's 611-bone merged hierarchy and local/world/inverse bind
matrices remain intact. Corrected hood-follow hair weights and the accepted
thigh-clearance/garment weights remain intact; hair geometry is unchanged.
Original runtime skeleton assets, playable animations, prefabs and controllers
are not overwritten by v0.1.x. See [stabilization record](docs/STABILIZATION_V0.1.3.md)
and current automated results (local artifact omitted).

The user confirms working tested gameplay/cutscenes, movement, aiming, weapon
handling, materials and lighting. v0.1.2 ADS hair/hood acceptance is tied to
installed hashes; all 80 currently installed natives were checked again and
match that baseline. This task performs no new game session. v0.1.3 installation
and wider action-by-action coverage still require the supplied manual checklist.

The objective for v0.2.0 is one recognisable original Bela/daughters idle on
the Grace-based character, with safe entry/exit blending and preserved playable
systems. More assertive posture should come from a visually confirmed original
clip. The source file's name alone does not establish its personality or usage.

Recovery: accepted ZIP (local artifact omitted),
`build/checkpoints/accepted_0.1.2/`, and Git branch `codex/accepted-v0.1.2` at
`4e747d986a5e0234b6a71be5dcfe7df0b772b827`. Keep v0.2 prototypes as a separate,
optional animation layer until accepted. Do not promote a new runtime baseline
on the strength of an offline export.

## 2. Verified animation-format findings

The local selective extracts contain 38 related RE8 resources and 24 inspected
RE9 resources. The read-only metadata adapter reports zero errors. It reads
headers, list indices, bank references and raw rest tables; it does **not**
decode keyframes/compression or prove playback. Full evidence:
RE8 headers (local artifact omitted),
RE9 headers (local artifact omitted), extraction manifests
`reports/re8_animation_research_extraction.json` and
`reports/re9_animation_research_extraction.json`.

| Item | RE8 observation | RE9 observation | Evidence and implication |
|---|---|---|---|
| MOTLIST | Suffix/header 486; 18 extracted lists | Suffix/header 1047; 11 extracted lists | Versions differ; no filename-only conversion |
| Embedded MOT | Header 458, magic `mot ` | Header 983, same magic | Shared family, distinct versions |
| MOTBANK | Header/suffix 3 | Header/suffix 4 | Actual bank IDs, types, mask bits and list references inspected |
| List indices | Motion ID/switch/mask/tag/flags | Same concepts plus additional index data | Preserve semantics; an index is not a controller state name |
| Source idle | 300 frames at 60 fps; 129 rest bones, 116 bone tracks | GeneralM caution idle: 814 frames at 60 fps; 70 rest bones, 68 tracks | Clip track count need not equal a mesh's full bone count |
| Joint maps | Related `.jmap.17` extracted | Face `.jmap.28` extracted | No cross-version semantic conversion established |
| Constraint resources | Not adapted by current pipeline | Original `.jcns.35` resources retained in game | Helper/IK/procedural bones need controller/constraint inspection |
| State machines | Filename examples `.fsmv2.40`, `.motfsm2.42` | Player TPS `.motfsm2.45`; grapple `.fsmv2.42` | Discovery only; graph semantics and active states remain unknown |
| Facial poses | Separate Bela-associated facial bank/list | Eye-pose list with neutral/close/squeeze-close | Body and facial compatibility are separate |
| Secondary motion | Related `.gpuc.62`, `.chain.39` | `.gpuc.250925365`, `.chain2.15` | No cloth/chain transplant validated |

The pinned research [MOT adapter](https://github.com/kagenocookie/RE-Engine-Lib/blob/ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef/REE-Lib/RszFile/MotFile.cs)
defines translation, quaternion rotation and scale tracks; bone index/hash,
compression/decompression cases, and raw rest translation/quaternion data.
Its quaternion representation uses XYZW and requires normalization/positive W
for its compressed writer. That encoding convention must be handled separately
from continuous quaternion interpolation. Actual local keyframe conventions
and runtime interpolation have not been experimentally verified here.

The [MOTLIST adapter](https://github.com/kagenocookie/RE-Engine-Lib/blob/ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef/REE-Lib/RszFile/MotlistFile.cs)
recognises both game versions, embedded MOTs, shared bone tables, motion trees,
reference links and newer optional MOTPACK references. Extracted facial/body
samples used embedded MOTs; no MOTPACK reference was needed in those samples.
This does not establish that all RE9 resources are embedded or interchangeable.

## 3. RE8 Bela animation inventory

The complete structured inventory is
bela_animation_inventory.json (local artifact omitted)
and CSV (local artifact omitted): **340 clip
records across selected related resources**, including base and `_ge` variants.
Records contain path, offset and motion ID/switch, associated rest-table hash,
duration from header frame count/FPS, track count, behaviour candidate,
dependencies, extraction state, suitability and complexity. Repeated names
across resource variants remain separate records; 340 is not 340 unique Bela
animations. Duration is nominal header time, not verified rendered loop timing.

Short path aliases used only in this table:

- **G:** `natives/stm/character/ch/animation/ch02_0500/motlist/ch02_0500general.motlist.486`
- **F:** `natives/stm/character/ch/animation/ch02_0500/motlist/ch02_0020facialbasic.motlist.486`
- **L:** `natives/stm/character/ch/animation/ch02_0500/analysisdata/ch02_0500_list.motlist.486`

| Priority / candidate | Path / motion ID | Nominal seconds | Bone tracks | Assessment |
|---|---|---:|---:|---|
| 1. `ch02_0500_General_Idle_Loop` | G / 0 | 5.000 | 116 | First decode experiment; shared-family idle candidate |
| Idle variation `_Idle_Emotion_v4` | G / 104 | 4.117 | 116 | Inspect after base idle; gesture/loop status unverified |
| Idle variation `_Idle_Emotion_v5` | G / 105 | 8.283 | 116 | Same gate; `_ge` counterpart also exists |
| 3–4. `_Emotion_Eldest_Provocative` | G / 200 | 3.700 | 111 | Likely relevant Bela gesture by label; usage/uniqueness unproven |
| `_Emotion_Eldest_Appearance` | G / 300 | 5.867 | 116 | Original upper-body/appearance candidate; may be scripted |
| `_Emotion_Eldest_Door` | G / 250 | 6.900 | 116 | Interaction-specific; defer controller integration |
| 5. `_Loco_Walk_F_Loop` | L / 1 | 5.100 | 112 | Analysis-data locomotion candidate; retail binding unproven |
| `_Loco_Run_F_Loop` | L / 12 | 1.100 | 107 | Later root/foot-contact work, not MVP |
| 6. `_FacialBasic_Normal_Idle_Loop` | F / 0 | 4.333 | 177 | Bela-associated face work; body MVP does not cover it |
| `_FacialBasic_Angry_Idle_Loop` | F / 2 | 3.350 | 177 | Expressions require independent mapping |
| `_FacialBasic_Laugh_Idle_Loop` | F / 8 | 6.983 | 177 | Mouth/lip and timing work required |
| 7. `_Freezes_Idle_IdleToIdle*`, `_RunToIdle*` | G / several IDs | Inventory | 116 in examples | Enemy freezing context; low suitability for Grace states |
| Attacks, damage, grapple, floating/flying | Related lists | Inventory | Inventory | Excluded from first playable prototype |

**Ownership evidence:** `ch02_0500.motbank.3` links General (bank ID 10),
Attack (20), Damage (30), AddDamage (31), Other (50) and MotionTree (100).
`ch02_0000_facial.motbank.3` explicitly references `ch02_0020FacialBasic`
and presentation/message list `c22_EM1262`. Corresponding facial banks/lists
for IDs 0100/0120 and 0200/0220 exist. Thus Bela-associated facial naming and
a shared daughters body family are supported by actual references. Exclusive
usage of an “Eldest” clip, use of the common idle by Bela in a specific state,
and shared-vs-unique decoded curves remain unverified. Do not label every
daughters clip Bela-exclusive.

All listed candidates were extracted from local official PAKs and have inspected
header metadata. None has decoded keyframes or a conversion result. Dependencies
are bank references plus inherited MOT bone tables; masks, events, constraints,
message/presentation references and source runtime state ownership need further
inspection. The inventory deliberately labels name-based behaviour as a
hypothesis. It does not prioritize attacks.

## 4. RE8 versus RE9 animation architecture comparison

| Dimension | Evidence | Required next verification |
|---|---|---|
| Hierarchy | Verified correction: source `Hip` and leaf `Null_Offset` are siblings under `root`; target has `root → Hip`. Body MOT rest table 129 vs source body mesh 185 bones; target GeneralM MOT 70 vs combined mesh rig 611 | Do not insert the source leaf into the pelvis chain. Preserve target Ankle → Foot → Toes intermediates and native helpers |
| Rest pose | 125 of 129 source idle bone names occur in Bela body mesh. Four hand/foot offset names do not. Maximum raw rest-translation difference is 76.16 mm against mesh local origins | Build and visually validate a clip-skeleton-to-mesh adapter. Rest tables are not automatically identical to the mesh bind pose |
| Coordinates | Mesh pipeline transposes file matrices into column-vector math; Blender applies its existing +90° X axis conversion | Verify MOT track absolute/additive, local/model space and quaternion composition independently |
| Transform encoding | Upstream adapter covers vector/quaternion/scale tracks with versioned compression | Decode exact selected clip, every track compression flag, sparse frame times and constant tracks |
| Interpolation | Track frame data and clip interpolation flags exist in primary adapters | Match runtime interpolation and boundary conditions; do not infer engine interpolation from Blender defaults |
| Root motion | Source root/offset hierarchy and locomotion clips exist | Measure root/hip curves and flags; choose explicitly in-place for first idle |
| Binding | Banks contain list paths/IDs/types/masks; Grace GeneralM bank entry is bank 0/type 0/mask 0 | Trace active motion layers/state graph and index invocation in RE9 |
| Graphs/transitions | Source motion-tree list contains non-MOT entries; TPS/FPS FSM filenames are discoverable | Decode graph references, blend durations, joint masks, events and state interruptions |
| Face | Different bone vocabulary, separate banks and blendshape sections | Verify procedural blink/expression blending, gaze layering and cutscene/lip-sync invocation |

The detailed rest comparison is
source_skeleton_comparison.json (local artifact omitted).
Its 76.16 mm residual is a measured static discrepancy, not a proposed scale
factor or proof of unusable animations. The mesh fitting scale of 0.9 must not
be applied automatically to every animation translation.

Grace's original eye movement, constraints, IK, hands and state machine remain
functional in the existing mod because their runtime assets are retained. That
is evidence for preserving them, not evidence that a different skeleton or
MOTBANK will bind correctly. Controller candidates are listed separately in
`reports/animation_research/re8_controller_candidates.json` and
`re9_controller_candidates.json`; their semantics have not been decoded.

## 5. Full-skeleton transplant feasibility: Architecture B

**Assessment: research-dependent, high integration risk; not recommended for
the initial implementation.** RE8 body mesh has 185 bones and face mesh 300;
neither is a drop-in substitute for the retained 611-bone Grace assembly.
No complete merged original Bela runtime rig/controller transplant was tested.
No native source animation-controller compatibility is established.

Potential benefit is preservation of original body/facial controls and garment
bone semantics. Costs include rebuilding animation bank/controller bindings,
joint maps, named/hash/index assumptions, constraints, playable IK targets,
weapon sockets/holsters, collision and facial resources. The source enemy
system does not establish coverage of Grace's reloads, traversal, interactions,
crouch, first-person paths or scripted scenes. Cutscenes may require target
bones and controls even when a source idle plays successfully.

[REFramework](https://github.com/praydog/REFramework) and its
[SDK documentation](https://curious-adventure.github.io/REFramework-book/)
are candidates for object/joint inspection and isolated invocation experiments.
They do not demonstrate a universal controller replacement or a ready-made
RE8-to-RE9 animation bridge. No hook was added here. Consider B only after A's
single-clip experiment exposes a specific unresolvable limitation and an
isolated B experiment proves gameplay/cutscene compatibility without replacing
the working release. Separate technical proof is required for every claimed
benefit; facial authenticity alone does not justify losing playable systems.

## 6. Recommended architecture: A, retained Grace skeleton

Retarget selected original tracks to Grace's current hierarchy and integrate
only one verified idle state first. This is a recommendation from local
structural/runtime evidence, not an already demonstrated animation conversion.

| Criterion | A: retarget to Grace | B: original Bela system |
|---|---|---|
| Preserve working mesh/controller | Strong starting point; existing v0.1.x remains base | Requires new integration contract |
| Weapon/IK/playable states | Preserve target states, constraints and attachment controls | Must recreate or bridge missing states and assumptions |
| Original motion fidelity | Needs explicit rest-axis/hierarchy correction | May retain source motion, but runtime binding remains unproven |
| Facial authenticity | Separate mapping still required | Original controls could help, but face resources/controller conversion still required |
| Incremental rollout | One slot/layer, optional overlay and disable path | Broad dependencies; harder isolation |
| Initial complexity | High; format/invocation stages research-dependent | Research-dependent throughout, with much larger scope |

Do not use `rigging.bone_mapping()` as an animation retargeter. Its ancestor
fallbacks, facial collapse and `Null_Offset → root` alias were suitable for
weight/geometry fitting. Simultaneous source root and offset animation cannot
be collapsed by simply overwriting one target track. The current landmark
position fit does not calculate animated bone-local quaternion conversion.

For the first prototype, preserve Grace finger/weapon/IK controls and native
target limb translations. Compose source hierarchy changes, retarget posture
rotations through validated local bases, and keep root motion explicitly
in-place. Evaluate whether full-body idle tracks or a safe upper-body mask best
preserve planted feet; make that choice from decoded source data and observed
target layers, not from filenames alone.

## 7. Relevant tools, repositories and documentation

| Tool/reference | Status | Appropriate use / limit |
|---|---|---|
| Project extractor + RE Asset Library | Pinned and locally used | Read-only official PAK extraction, dependency hashes; not an animation decoder |
| Portable Blender 4.3.2 | Pinned and locally used | Original/current rig inspection, pose evaluation, renders; independent animation import test still needed |
| RE Mesh Editor v0.66 | Pinned and locally used | Current native mesh/MDF/TEX pipeline; blendshape import explicitly disabled as broken |
| [ReeLib](https://github.com/kagenocookie/RE-Engine-Lib/tree/ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef) | Read-only source snapshot inspected | MOT/MOTLIST/MOTBANK adapters; source presence is not this project's writer/runtime proof |
| [REE Content Editor](https://github.com/kagenocookie/REE-Content-Editor) | Upstream documents Village/Requiem and animation support | Candidate original-clip decode/preview/import/export; exact samples must be tested |
| [Animation tools guide](https://github.com/kagenocookie/REE-Content-Editor/wiki/Animation-tools) | Upstream documented | Recommends GLB/GLTF for animations; warns retargeting is incomplete and limited to renaming/small transform changes |
| [RE-Engine-010-Templates](https://github.com/alphazolam/RE-Engine-010-Templates) | Alternative primary format reference | Cross-check headers/track layouts when decoder results disagree; not a runtime compatibility guarantee |
| [RE Chain Editor](https://github.com/NSACloud/RE-Chain-Editor) | v14 changelog names RE9; repository archived April 2026 | Candidate chain/CLSP inspection only; native GPU cloth and cross-rig behaviour need separate proof |
| REFramework, existing local setup | Existing runtime tool; unchanged | Read active bank/layers/joints; any future script stays in optional prototype layer |

Production pins remain in `config/toolchain.lock.json`. Research source pin and
file hashes are in `config/animation_research.lock.json`, commit
`ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef`. The research clone under
`tools/research/RE-Engine-Lib` was not installed into the game or made a
production dependency. Existing project utilities are reusable for extraction,
hashes, source/target mesh reading and offline QA. A decoding/retargeting/native
writer proof is still required; no new conversion tool is promised.

## 8. Proposed reusable conversion pipeline

| Stage | Reusable part / proposed output | Gate | Complexity |
|---|---|---|---|
| RE8 selection/extraction | Existing extractor; hash-identified clip/list/bank | Already available for first idle; prove usage/recognition visually | Low |
| Decode original animation | Candidate editor/ReeLib; untouched original preview + decoded tracks | All compression modes, times, hierarchy and events accounted for | Research-dependent |
| Neutral representation | Proposed GLB plus explicit metadata/arrays: seconds, XYZW unit rotations, translations, hierarchy/rest matrices, source IDs and flags | Decode/re-encode original with bounded curve error; no silent dropped channels | Medium |
| Skeleton/coordinate adapter | Proposed reviewed mapping and basis corrections | Rest pose, root/offset collapse, helper handling and local/model semantics proven | High |
| Animation retargeting | Proposed target tracks on unchanged Grace rig | Target offsets/limb lengths preserved; posture and feet reviewed | High |
| Blender validation | Existing rig/render/geometry tools plus actual clip playback | Source and target side-by-side at rest/start/middle/end and loop seam | Medium |
| Native RE9 resource | Candidate MOT 983 in MOTLIST 1047, preserving bank/index/masks/events | Untouched RE9 roundtrip first; output reopen and dependency validation | Research-dependent |
| Isolated runtime invocation | Separate reversible prototype overlay | Live binding, entry/exit, interruptions and gameplay controls proven | Research-dependent |

Proposed canonical math uses column-vector matrices and documented units.
First identify whether decoded keys are absolute local transforms, additive
deltas or model-space values. Evaluate animated source globals from the actual
hierarchy, account for intermediary bones, and derive target locals with
`L_target(t) = inverse(G_target_parent(t)) * G_target(t)`.
For rotation-only local tracks a candidate rest-relative basis conversion is
`R_target(t) = R_target_rest * A * DeltaR_source(t) * inverse(A)`;
the definitions of `DeltaR_source` and basis `A` must be calibrated from the
decoded convention. These are proposed mathematical checks, not implemented
or universally valid engine formulas. Preserve target limb offsets rather
than copying all source translations, then validate any IK correction.

Keep quaternion sign continuity during sampling/interpolation; q and -q
represent the same orientation. Apply a writer's positive-W requirement only
at its encoding boundary and verify the decoded angular curve afterwards.
Handle sparse keys, constant tracks, scale and loop end-time conventions.
Measure root motion instead of zeroing every hip translation. In-place root
suppression is a deliberate first-idle choice, not a general locomotion policy.

## 9. Minimum viable prototype specification

**Source:** base G list above, `ch02_0500_General_Idle_Loop`, bank ID 10,
motion ID 0, switch 0, list slot 0, embedded offset **0x1d0**, MOT 458;
300 frames/60 fps, nominal 5 seconds, 116 tracks, 129 rest bones.
The exact resource SHA256 is recorded in the structured inventory. Use the
base resource, not the `_ge` duplicate. It is a shared-family candidate until
playback confirms Bela-relevant appearance/usage. Do not call it unique Bela.

**Possible target for inspection, not an approved replacement slot:**
`natives/stm/animation/ch/ch02/ch0200/motlist/ch0200_generalm.motlist.1047`,
`ch0200_GeneralM_0000_Idle_caution`, bank 0, motion ID 0/switch 0.
Its name, bank entry and header were read; its current live state/layer binding
was not captured. Source bank/motion IDs must not be transplanted onto target
IDs without understanding the target invocation.

**Milestone A — decode/source proof (research-dependent).** Load the exact
source clip and its own 129-bone MOT rest table with a supported decoder.
Reconstruct it on the correct source rig/mesh and export a 60 fps GLB preview.
Check rest alignment, all 116 tracks, source start/middle/end and loop seam;
record unsupported channels and visual characterisation. Compare original
tool playback to Blender. No retargeting or game writes in this first experiment.

**Milestone B — retarget/offline proof (high).** Map core body rotations with
reviewed bases, compose root/offset hierarchy, preserve target translations and
611-bone binds, and handle hand/foot offsets explicitly. Review a full loop for
twisted arms, shoulder distortion, foot drift, pelvis displacement, skirt folds,
hood motion and protected weapon/IK controls. Proposed review tolerances are
unit-quaternion error below 1e-5, target length change below 1%, planted foot
drift below 10 mm where source contact is intentional, and suppressed root
drift below 1 mm. These are adjustable engineering gates, not game standards.

**Milestone C — native/resource proof (research-dependent).** First roundtrip
an untouched target idle through the chosen tool. Verify all original list
entries, IDs, flags, masks, events, reference links and curves survive. Then
write one converted clip using target formats and bind references, reopen it,
and compare sampled output to offline target motion. Proposed encoding error
bounds: 0.1° angular and 1 mm positional, subject to observed native precision.
All non-replaced clips must retain their decoded behaviour and dependency
semantics. A parseable file alone does not pass this milestone.

**Milestone D — runtime proof (research-dependent).** Confirm the live Grace
idle layer/bank/state before choosing a reversible non-critical test slot.
Use a separate optional prototype overlay and preserved original target
resource. Verify entry/exit, loop blending, idle interruption by move/aim,
crouch, interaction, cutscene ownership, clothing/hair and attachments. Disable
the overlay and confirm normal v0.1.3 behaviour without save/controller damage.
Only a recorded successful runtime test passes D. Expand scope only afterwards.

## 10. Facial animation as a separate workstream

Verified: Bela's source face/lashes have FACIAL eyelid influences; Grace's
face/lashes use `L/R_UprLd_*` and `L/R_LwrLd_*`. Current exports collapse
FACIAL influences onto Head_0 while preserving L_Eye/R_Eye, explaining why
gaze can work independently of blink. Both original meshes contain blendshape
sections, but the pinned reader disables their import as broken. Current
replacement face has no exported blendshape section.

Grace's face prefab resource tables refer to
`Animation/ch/ch02/ch0200/facial/motbank/ch0200_10.motbank`.
The actual `.motbank.4` and eight `.motlist.1047` files were extracted. The
eye-pose list contains 11 one-frame poses, including neutral, close and
squeeze-close, each with 229 tracks and a 60 fps header. That is verified pose
metadata, not a timed blink animation. Gameplay trigger frequency, gaze/close
mixing, eyelid keyframes and cutscene overrides remain unknown. See
facial findings (local artifact omitted).

| Facial feature | Proposed investigation | Complexity |
|---|---|---|
| Blink | Decode original Grace neutral/close; reproduce closure; transfer only Bela lid/lash weights to verified target controls, preserving gaze and rest likeness | High, runtime trigger research-dependent |
| Eyebrow | Map source brow controls to target brow/sack bones; preserve neutral expression | High |
| Jaw/mouth | Distinguish C_Jaw/teeth/tongue motion from source facial controls; verify lip geometry | High |
| Expressions/morphs | Inventory source/target morph names/deltas and graph bindings with a reliable reader/writer | Research-dependent |
| Eye movement/gaze | Preserve existing L_Eye/R_Eye; verify gaze layering during closure | Medium |
| Cutscene expressions | Trace scene tracks and overrides separately from playable facial bank | Research-dependent |
| Lip-sync | Establish dialogue/timeline facial channels and phoneme/expression binding | Research-dependent |

Prefer target skeletal blink controls if decoded closure can be made natural
on Bela; compatible morph authoring is an alternative only after its mechanism
is proven. Require full bilateral closure, no eyeball penetration at several
gaze directions, coherent lashes/corners, unchanged neutral likeness and
gameplay/cutscene tests. Do not infer that restoring bone names alone gives
correct eyelid arc or timing. Defer if it requires the larger face pipeline;
successful body idle conversion does not pass any facial compatibility gate.

## 11. Milestones, dependencies and feature complexity

| Work item | Complexity | Dependency / technical reason |
|---|---|---|
| Protect/rebuild v0.1.x | Low; completed | Exact native identity and accepted recovery archive verified |
| Metadata inventory | Low; completed | Headers/banks are inspected; no compressed curves decoded |
| Original idle decode/preview | Research-dependent | Exact decoder, sparse keys/compression and source skeleton adapter |
| Rest/bone-space mapping | High | Different names, intermediary/helper bones and measured rest discrepancies |
| One idle retarget | High | Requires correct axes, target offsets, contact and loop treatment |
| RE9 untouched roundtrip | Research-dependent | Validate writer on exact 983/1047 resources and preserved list semantics |
| Live state/bank binding | Research-dependent | Target FSM and layered/procedural behaviour not decoded |
| Safe transition integration | High | Idle interruption, blending, masks and interaction/cutscene ownership |
| Eyelid/lash adaptation | High | Independent closure and neutral/gaze constraints |
| Morph/full face pipeline | Research-dependent | Current reader disables blendshape import; controller links unknown |
| Locomotion retargeting | High | Root motion, direction/speed blending and foot IK; later than MVP |
| Advanced cloth/hair | Research-dependent | Topology/control points, native registration, collisions and version conversion |
| Full source skeleton/controller | Research-dependent | Recreates playable contract and has broader failure modes |
| Release/recovery automation | Medium | Preserve optional overlays, exact dependency manifests and acceptance scope |

Dependency order: **baseline → A/source reconstruction → B/offline retarget →
C/untouched roundtrip and native asset → D/live invocation and transitions →
one-idle acceptance**. Facial work branches after original neutral/closed-pose
decoding and can progress independently; it is not implicit in body milestone B.
No timeline estimate is credible until A and the target writer roundtrip pass.

## 12. Risk register

| Risk | Level | Detection / mitigation |
|---|---|---|
| Common idle is not recognisably Bela or not invoked by her | Medium | Preview and verify source usage before choosing release clip; retain Eldest candidates for comparison |
| Mesh bind pose mistaken for animation rest pose | High | Measured 76.16 mm discrepancy; reconstruct original source clip before fitting target |
| Root and Null_Offset collapsed incorrectly | High | Compose hierarchy transforms; inspect root curves and contact |
| Quaternion axis/order/sign error | High | Basis calibration, unit/sign continuity checks and sampled angular comparison |
| Writer silently drops channels/events or changes shared clips | High | Untouched native roundtrip, complete list comparison, unsupported-channel failure |
| Wrong motion IDs/masks/layer registration | High | Trace actual live bank/state; preserve original target indices and mask contracts |
| Foot drift or gameplay movement mismatch | High | In-place idle first; contact metrics and movement/IK tests |
| Weapon/IK/first-person state interference | High | Preserve target states/control bones; interrupt prototype on protected states; test all weapon actions |
| Existing hood/dress correction regresses | High | Native payload/hash protection; current pose suite plus actual converted loop and runtime ADS |
| Face closure/gaze/morph damage | High | Separate workstream, rotating-eye clearance tests and neutral-face comparison |
| Tool support appears broader than tested | High | Pinned versions; exact file tests; upstream retargeter limitation is recorded |
| Game patch changes resources/controller semantics | Medium | Record game build and archive/resource hashes; invalidate acceptance on changed inputs |
| Optional physics/full skeleton expands MVP scope | High | Require isolated proof; keep outside single-idle definition of done |

## 13. Testing and validation strategy

**Decode:** check bounds/magic/version, all track hashes/indices, finite values,
frame times, sparse/constant keys and flags. Compare original preview with
decoded sampling at start/middle/end, extrema and loop seam. Explicitly mark
unknown channels and fail rather than silently omit them. Preserve source
resource hashes and clip identity in every derived artifact.

**Retarget:** verify rest reconstruction, hierarchy composition, target local
transforms, normalized quaternions, limb offsets/lengths, root treatment,
contact and helper/mask treatment. Evaluate actual clip playback in Blender
with body, face, dress, hood, hair, gloves and Grace boots assembled. Retain
the existing 14 body/14 headwear fixture suite and seam audits for regression,
but do not substitute synthetic poses for real animation playback.

**Native:** prove an untouched target roundtrip first. Decode the written clip
and compare time samples, rotations/translations, list indices, masks, events,
trees/references and resource dependencies. Check preservation of all unused
entries and Grace bind definitions. Repeated file parsing alone is insufficient.

**Runtime:** record game build, exact overlay/base hashes, camera/outfit/mod
settings, original/live state IDs and video. Test idle loop and enter/exit;
walk/run/turn, aim/fire/reload/holster, crouch/stand, interactions, traversal,
first-person transitions and at least one previously working cutscene. Inspect
head/neck, shoulders/sleeves, wrist/grip, pelvis/thighs/knees, hood/hair, gaze,
materials/alpha and floor contact. Preserve intentional costume construction.
Confirm disable/re-enable and rollback. Do not claim runtime success from
offline poses, file integrity, user screenshots of another build or a tool's
general supported-game list.

Keep aggregate engineering metrics and only targeted failures in summaries.
Store detailed diagnostics/video references separately; avoid per-vertex logs.

## 14. Definition of done for v0.2.0

The first v0.2.0 release must satisfy all of the following:

1. One visually confirmed original Bela/daughters idle is identified by exact
   path/hash, bank/list/motion ID and decoded track/rest conventions.
2. The original and retargeted clip play correctly offline; target Grace
   hierarchy/binds and protected gameplay controls are preserved.
3. A native RE9 animation resource reopens and reproduces the validated target
   curve; untouched roundtrip and preservation of unused resource semantics pass.
4. Actual RE9 runtime evidence shows the idle, stable transitions and protected
   movement/weapon/interaction/cutscene behaviour for documented test scope.
5. The animation layer is optional, hash-manifested, reproducible and reversible
   without save changes or replacement of official archives.
6. The accepted v0.1.x base remains recoverable; no hood/thigh/neutral-face
   regression is introduced. Known garment limits remain accurately documented.
7. Facial success is reported separately. Blinking/full expressions/cloth are
   included only when their own gates pass; they are not implied by body idle
   success and are not mandatory to declare the narrow body prototype complete.

Expanding into locomotion/gestures before the one-idle runtime proof fails this
scope. If native writing or binding remains unresolved, deliver an honest
offline research prototype; do not call that a completed v0.2.0 runtime release.

## 15. Verified facts, open hypotheses and future scope

**Verified:** accepted v0.1.2 identity/recovery; reproducible 80-file native base;
retained 611 Grace binds; actual 486/458 versus 1047/983 sample headers; real
body/facial bank references and clip IDs; original lid weights and Grace named
closed poses; blendshape pointers; current skeletal-only garment; 340 related
clip inventory records; source-rest/mesh discrepancy. Upstream reader/writer
and editor claims are labelled separately.

**Not established:** source clip Bela-exclusive usage/recognition; keyframe
coordinate/rotation and interpolation conventions; complete compression
support on selected samples; native converted clip output; live target idle
ownership; gameplay blink trigger/blending; complete facial/morph conversion;
source GPU cloth bindings; controller/IK/cutscene compatibility after animation
replacement. These are experiments, not assumptions or completed features.

Optional later scope: more original movement/gestures, advanced dress and hair
secondary motion, complete expressions and lip-sync, stronger cutscene coverage,
and reusable cross-generation adapters. Voice/dialogue replacement requires
properly authorized/licensed material and its own integration task. Each is
high or research-dependent because it adds controller, topology, timing or
resource contracts beyond the one-idle prototype. The v0.1.x model remains
useful even if these prove impractical.

## 16. Specific user inputs and exact first authorised experiment

No additional source files are needed to **start source-clip decoding**: the
chosen list, source meshes, banks and tools/reference code are already local.
Do not ask for a new source-game dump. Further original controller/JMAP/UVAR
resources should be selectively extracted from the existing owned PAKs when
their exact references are identified; an incomplete filename list is not
proof a resource does not exist.

Inputs needed before **runtime integration/acceptance**:

- Confirm the new v0.1.3 installation with its manual checklist; report exact
  failing action/scene if any. This establishes the accepted base for v0.2 work.
- Provide or capture a reproducible non-critical RE9 idle scene, game build,
  outfit/camera and enabled mods. An existing save may be read for testing; no
  save editing is needed. The exact non-critical test state is not chosen yet.
- Capture read-only REFramework data for active Grace motion banks/layers,
  state and bank/motion IDs, joint names and root/IK handling. For blinking,
  record open→closed→open lid transforms, gaze layering and controller/pose
  invocation. Missing evidence is runtime state, not source geometry.
- After source preview, confirm whether the common idle expresses the desired
  Bela characterisation. Default is the five-second common idle; compare the
  Eldest gesture only if it fails that requirement. No selection is needed
  before the default source reconstruction experiment.
- Explicitly authorise v0.2.0 implementation before a retargeter/native output
  or runtime integration is built. This roadmap does not itself authorise it.

**First experiment after authorisation:** open the exact base
`assets/extracted/re8/natives/stm/character/ch/animation/ch02_0500/motlist/ch02_0500general.motlist.486`
in the candidate supported animation tool, select **motion ID 0 / switch 0 /
slot 0**, `ch02_0500_General_Idle_Loop` at **0x1d0**, decode its **116 tracks**
using its **129-bone MOT rest table**, reconstruct original source playback,
and export a **60 fps, nominal five-second GLB preview** for Blender comparison.
Confirm rest/start/middle/end and seamless loop behaviour against the tool's
original preview; log four hand/foot offset bones and any unsupported tracks.
Stop at source reconstruction if conventions or source/mesh binding disagree.
Do not generate an RE9 replacement or change an installed resource in this
first experiment. That concrete result decides whether milestone B is justified.

