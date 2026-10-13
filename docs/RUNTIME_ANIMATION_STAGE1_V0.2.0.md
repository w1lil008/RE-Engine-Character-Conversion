# Milestone D Stage 1 — runtime binding preparation

## Status and boundary

**The exact live Grace idle binding is pending a read-only game capture.** RE9
was closed during this investigation. No bank, layer or motion identifier is
presented as the active gameplay idle. Stage 1 has produced the instrumentation,
baseline checks and a gated experiment plan. The native animation remains
unregistered and inactive. A playback harness and installable replacement cannot
be finalized safely until the missing live evidence is collected and reviewed.

Accepted checkpoints remain `44eb9e1` (source), `e579c25` (retarget) and `91ee9fe`
(native conversion). Their protected files and the v0.1.2/v0.1.3 archives pass
the hash gates. Nothing in Stage 1 changes mesh geometry, skin weights, the
611-bone rig, hair/hood or thigh clearance.

The local target is Steam app **3764200**, build **23634047**, executable
file/product version **1.3.1.0**. The installed REFramework log records
**d1461375aee4ec3f313170f8eaad12064eb542d9**, tag v1.5.9.1 +507 commits,
16 September 2026 build, and **TDB83**. Executable/DLL hashes are in
`reports/runtime_binding_v0.2.0/environment_before.json`. The log describes
an earlier session; it contains no usable live animation capture.

All 80 installed loose native character files match both releases, because
v0.1.3 has the same payload as v0.1.2. Those matches do not establish which
package label was installed or confer new runtime acceptance. v0.1.2's recorded
acceptance covers the ADS hair/hood correction. **Explicit v0.1.3 in-game
confirmation remains pending.** There are 90 protected installed files and
14 files under the identified Steam save location. Other possible save
locations are not asserted. Official archives were only opened for reading;
their size/mtime inventory is checked, rather than claiming whole-archive
content hashes.

## Static architecture: verified resources, unresolved live selection

| Evidence | Verified static finding | Live question |
|---|---|---|
| `ch0200.motbank.4` | GeneralM bank ID 0/type 0/mask 0; additive GeneralM bank 2000; GeneralH 100; Emote 50; MotionTree 10; Gimmick 500 | Which entries are loaded/selected for this scene, weapon and camera? |
| `ch0200fps.motbank.4` | 56 list descriptors; separate L/L2 FPS banks also exist | Which component drives visible FPS arms versus body? |
| GeneralM slot 0 | `0000_Idle_caution`, motion 0/switch 0, 814 frames at 60 FPS | Does ordinary stationary gameplay select it, and on which layer/mask? |
| GeneralM slot 1 | `0001_Idle_Loop_VerB`, motion 1/switch 0, one frame | A static pose is not proof of the live repeating idle |
| Other idle candidates | Crouch, additive/breathing, upper-body, weapon and danger variants exist | Capture blend contributions and changes when aiming/moving |
| Nine MOTFSM2.45 files | FPS base/add/upper/left-upper/weapon-upper; TPS base/add/upper/left-upper; 577 transition records | BHVT node actions and actual active nodes/conditions are not established |
| Transition continuation data | Recorded continuation layer/mask pairs are (0,0) | These fields do not describe every node's affected joints or active layers |

Bank ID 0 is reused with different type/mask descriptors and different
MOTLISTs. Always retain the tuple **object identity, layer/node, bank ID,
bank type/type mask, loaded list path, motion ID, switch and joint mask**.
An ID alone is insufficient. The capture also needs actual advancing frames,
motion names, camera mode, weapon state and stationary/movement/aim markers.

The pinned REFramework source has RE9 SDK layouts, but offsets and layouts
are not used for raw-memory reads in our script. SDK reflection establishes
method availability in the actual process. REFramework support does not prove
that every older-game motion API is implemented in RE9.

## Joint maps and procedural dependencies

Two original JMAP28 resources were extracted into a fresh workspace directory
from the official base archive, using highest-official-patch lookup:

* `GameAssets/Character/CharacterPrefab/cp_A1/cp_A100/JointMap/cp_A1JointMap.jmap`
* `GameAssets/Character/CharacterPrefab/cp_A1/cp_A100/JointMap/cp_A1JointMap_ForConvert.jmap`

The first contains **60 mask groups**, attributes 10. The conversion map
contains **four groups (0–3)**, attributes 0. Group 0 contains 74 entries;
groups 1–3 contain 48, 64 and 84. Both contain 12 extra-joint records, zero
joint expressions and **zero embedded IK-motion definitions**. A bounded
Python reader and the pinned ReeLib reader agree on every mask hash, mask
byte and float32 weight. Complete decoded tables remain in the reports.

The mask bytes include values such as 2 and 3 and fractional weights; they
are not interpreted as simple enabled/disabled booleans. Mask group 0 in
the conversion map is not automatically the full-body gameplay mask.
The relationship between the MOT's conversion-map reference, runtime
deformation map and layer mask must be observed. Names are resolved only
where hashes occur in the native 70-bone rest table; unknown names stay
unknown. No extra joints or masks were rewritten.

Native conversion preserves 12 animation-only helpers, including weapon,
camera, ground-angle, hand-target and leg/hand IK names. The new idle has
24 body rotation channels and root translation; it does not animate fingers,
weapons or IK targets. Missing tracks retaining a target rest pose offline
does not prove that runtime blending retains their current procedural values.
Capture component types/fields for motion, IK, weapon and attachment systems.
The location, update order and effectiveness of live IK remain unresolved.

## Read-only diagnostic setup — safe to run now

The script is
`<LOCAL_PROJECT_ROOT>\scripts\runtime\bela_binding_probe.lua`.
It is also in the Stage 1 ZIP under `diagnostics/`. **There is no diagnostic
installation step and no autorun script.** REFramework's pinned ScriptRunner
uses an ordinary file picker and can run the workspace file directly.

1. Launch RE9 normally with the existing character mod. Use an existing Grace
   save in a quiet room, clear of enemies, cutscenes and scripted sequences.
   Record the exact room/chapter/save slot, camera setting and equipped weapon.
   Avoid saving during the diagnostic sequence; ordinary game autosaves are
   outside this script's control and must be distinguished from script writes.
2. Open REFramework (the installed menu hotkey, normally Insert), expand
   **ScriptRunner**, click **Run script**, and select the absolute Lua path above.
   Load it once. Loading again reuses its existing instance.
3. In **Script Generated UI**, open **Bela D1 — read-only binding capture**.
   Enter the scene/camera/weapon context. Click **Discover motion components**.
4. Select the actual Grace body component using its GameObject name, joint
   count and Object Explorer identity. A 611-joint count is supporting evidence,
   not a character identifier. Also select the FPS arms component if present.
   Use **Watch as body** and **Watch as FPS arms**. At most four objects can be
   watched. Discover again clears the selection. Confirm the identity checkbox
   only after checking the selected objects. If identity is ambiguous, stop and
   retain the API catalog; do not choose by a filename alone.
5. Click **Start bounded capture** and close the overlay while performing each
   action. Mark each interval with the UI buttons: **idle** for 15–20 seconds,
   **walk** for 3–5 seconds, **idle_after_walk** for 10 seconds, **aim** for
   3–5 seconds, **idle_after_aim** for 10 seconds. Mark before the action, then
   dismiss the overlay and perform it. The timing includes menu delay; inspect
   actual motion/frame changes, not the marker alone. Optionally capture reload
   and a harmless interaction with their markers if the chosen scene permits.
6. Click **Stop and save**. The UI reports the exact JSON filename under
   `<RE9_INSTALL_DIR>\reframework\data\bela_d1\`.
   Repeat separately after a camera change if FPS/TPS comparisons are available.
   Preserve the fresh REFramework log with that capture. Return the JSONs and
   room/camera/weapon information for analysis.
7. Deactivate the diagnostic by stopping capture, then exit the game. The Lua
   callback does no reads when stopped and disappears on process exit. It was
   never installed in autorun. Avoid **Reset scripts**, which would also reload
   unrelated scripts. Diagnostic JSONs can be retained or removed individually.

No generated MOT/MOTLIST is copied to the game for this capture. No animation
setter, hook, resource creation, bank registration, controller update, speed
change, pause or save API is called by the probe. It writes only new diagnostic
JSONs through `json.dump_file`, confined by REFramework to its data directory.
Existing capture filenames are checked before saving.

The installed unrelated `re9_remove_the_girl.lua`, Re9Minimap, Re9Nav and
ReShade/RenoDX files are inventoried and left intact. Do not reset or disable
them without recording an explicit separate configuration. They remain
potential environmental influences, not assumed animation conflicts.

### Scope and API gaps

The script verifies parameter count/types and instance/static status against
the current TDB, caches metadata, and invokes only a fixed read-only whitelist.
It first reads the actual game name, REFramework commit and TDB version through
verified SDK bindings. A mismatch or missing identity blocks scene queries.
These observed identifiers are separate from the expected Steam/executable
build, which is checked by the offline installed-file snapshot.
Getter names sourced from EMV are **candidates**, not asserted RE9 APIs.
It records loaded Active/Dynamic bank descriptors where exposed, list resource
strings, motion layers/nodes, playback frames, scalar states/masks/blend fields,
and selected object's motion/IK/weapon component metadata. Unsupported object
values are identified as references with undecoded contents. Missing getters
and exact method/field signatures remain in the catalog. A failed method is
disabled for the session and the failure is recorded.

Sampling is bounded to 600 samples/120 seconds at a nominal 5 Hz host-clock
rate, 16 layers/object, four nodes/layer where a node-count API is available,
and 2,500 engine calls/sample. Without node count, only documented node 0 is
read. Arrays/components have explicit caps and truncation is marked. Three
samples over 20 ms stop capture. Actual runtime cost is unmeasured until run;
stop immediately if the diagnostic affects play. It does not enumerate the
whole scene every frame or dump every bone.

The capture contains **sampled state changes**, not every controller transition
or blending event. Host `os.clock` is labeled separately from engine frames;
frame units and engine speed must be checked before treating them as seconds.
FSM node state, joint-mask contents, IK internals and cache residency may not
be exposed through these getters. They remain missing if absent. There is no
claim that the script captures all blend inputs or the global resource cache.

If discovery returns no objects or required values are missing, save the
catalog and use **Object Explorer** read-only: inspect the selected Motion,
MotionLayer/MotionNode, MotionFsm2 and IK/attachment component types. Record
the exact getters/fields and observed values for the missing binding tuple.
Do not invoke setters, changeMotion or editable value widgets. If the catalog
cannot resolve the API, **Object Explorer → Dump SDK** provides a matching
TDB/RSZ schema for offline investigation (use in a paused safe scene; the dump
can be expensive). Return the dump directory and log; do not substitute an
older game's SDK schema. These are the exact remaining instrumentation inputs.

Capture analysis command, from the project folder:

```powershell
$projectPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $projectPython scripts/runtime_stage1.py --capture 'ABSOLUTE_CAPTURE.json' --report 'reports/runtime_binding_v0.2.0/live_capture_analysis.json'
```

The analyzer lists missing switch/mask/type/path/frame/identity evidence and
cross-checks original descriptors. It never authorizes playback automatically.
A synthetic fixture or a static ID cannot become live proof. The scene and
camera are deliberately unset in the experiment configuration until this data
is reviewed; no specific room has yet been confirmed as the test scene.

## Integration methods and recommendation

| Method | Assessment | Requirement before use |
|---|---|---|
| Fresh MOTLIST path + component-local dynamic bank + one-shot layer invocation | Preferred research direction; no official resource/controller substitution; ordinary FSM remains in place | Verify RE9 class/setter/registration signatures, unused bank ID, selected layer, stop/release behavior, mask and FSM ownership |
| Temporary extra layer/state override | Higher risk: update order, blending, IK and ownership can interfere with playable systems | Proven layer lifecycle and immediate abort/release; no persistent puppet mode |
| One-slot native MOTLIST overlay | Reversible by removing overlay and restarting, but changes every user of that slot and retains cached replacement until restart | Live binding proof; preserve unrelated clips, aliases, bone table and original events; explicit event/timing plan |
| Mod manager installation | Convenient rollback only after an exact overlay is established | Confirm loose-resource routing and manager version/configuration; no bulk old-package replacement |
| Whole bank/controller replacement | Unnecessary scope for the first experiment | Not prepared or recommended |

EMV demonstrates dynamic banks and `changeMotion` in other RE Engine titles.
Its documented supported-games list does not establish RE9 support. Do not
install EMV as part of this stage or copy its puppet/resource-clearing helpers
into the working gameplay controller. The probe records available method
signatures without invoking integration methods.

The preferred first playback is a **component-local, one-shot invocation of a
fresh MOTLIST**, only if live inspection verifies that the intended idle layer
can accept it while its normal controller continues owning gameplay. A request
that is immediately overwritten by the FSM is a failed experiment; do not
fight it with repeated forced calls, speed changes, controller hooks or puppet
mode. Stop and investigate a genuinely isolated viewer/test context if needed.
No harmless spare layer or unused bank ID is assumed to exist.

No invocation Lua is emitted with guessed APIs. The preparation package holds
the accepted resources, method requirements and unfilled binding configuration.
Once live evidence establishes those requirements, a narrowly bounded playback
harness can be prepared for the user's separate activation authorization.

If dynamic invocation is unavailable, a replacement overlay is a later fallback,
not a ready install. GeneralM original caution idle is 814 frames with 68 bone
tracks and CLIP90 gameplay/event metadata; Bela is 300 frames with 25 body
channels. A blind replacement can change action cancellation, upper-action
completion, look-at and breathing behavior. Upstream whole-list writing also
normalizes unrelated data. Any fallback must preserve original unrelated MOT
blobs/index aliases and implement explicit shared-rest-table relocation and
event/timing handling, then pass independent preservation/reimport tests.

## Native loading requirements and remaining format risks

The candidate runtime resource path is
**`Animation/bela_prototype/v020/bela_idle.motlist`**, with a prospective loose
file destination
**`natives/stm/animation/bela_prototype/v020/bela_idle.motlist.1047`**.
This is a proposed fresh path, not a verified live binding or installed path.
It contains an embedded MOT983 and 70-entry native rest table, referring to the
original conversion JMAP. The standalone `.mot.983` is an inspection artifact;
no separate disk MOT is required by the embedded layout demonstrated offline.
There is no registered MOTBANK or assigned runtime bank ID. Motion 0/switch 0
are the candidate's local descriptor only. Zero mask/tag/flags are not proof
of appropriate live full-body behavior. Case/path/extension resolution and
loose-file loading need an engine observation.

The converted clip is five seconds, 301 samples from frame 0 to 300 at 60 FPS.
Full XYZW quaternion encoding is retained for **R_Arm_Clavicle** and
**L_Leg_Upper**. Both independent parsers accept it; it was not observed in
the 211 original GeneralM clips examined. The left thigh quaternion crosses
W=0. Runtime support remains unknown. An XYZ-only trial exceeded the accepted
precision gate, so it is not a permissible workaround. Do not resave through
the upstream writer that coerces full quaternions into XYZ.

Other unresolved risks are runtime interpolation/sign handling, actor-root
extraction of periodic sway, shared/native rest-table versus procedural binding,
mask interpretation, skin deformation after helper/IK layers, cache lifetime,
controller overwriting a direct request, and event behavior in the chosen state.
The accepted root's periodic X/Z motion is preserved, with no accumulated
locomotion. Its floor offset and loop residual are inherited from the accepted
retarget, not silently zeroed.

## First playback experiment — future authorization required

The immutable resource bytes and structured prerequisites are in
`build/animation_v0.2.0/runtime_stage1/preparation/` and
`dist/BelaGrace_RuntimePreparation_0.2.0_Stage1.zip`.
The archive is a review/preparation package, not a Fluffy mod: no root
`natives/`, modinfo, controller, bank or autorun payload. Extract it in a new
workspace folder. Do not unpack it into the game directory.

Before any activation, review the live JSONs, record the precise binding and
test scene, verify the installed build/DLL and protected hashes, choose an
unused component-local bank ID from observed data, and validate a harness's
exact APIs/abort path. Obtain the user's playback authorization. No timeout or
passing test substitutes for that authorization.

**Installation after that gate:** with the game closed, verify the proposed
destination does not exist and no active mod supplies it. Copy only the
manifest-verified candidate MOTLIST to the new path above, leaving existing
files intact. A newly staged file is not registered or invoked until the
approved harness explicitly loads/registers it. The harness must be manual-load,
disabled by default, scoped to the confirmed object/build, and record all
temporary additions. This stage contains no installer or executable harness.

| Test | Minimal operation and required evidence | Stop condition |
|---|---|---|
| A: load | With original Grace playback unchanged, load only the new MOTLIST through a verified resource API. Record resolved path/descriptor, load result and log; compare original resource access as control. Do not call a play method. | Loader failure, missing dependency, unexpected resource sharing or controller change |
| B: decode | Use a verified engine decoded-track access or isolated preview/sampler if exposed. Measure clavicle/thigh full XYZW tracks, especially W=0, against accepted sampled transforms. Raw file-parser success is insufficient. | Unsupported format, nonfinite rotations, wrong sign/pose, or no reliable decoding evidence |
| C: playback | Trigger exactly one 0–300 frame cycle on the verified compatible layer, with no forced looping or repeated motion requests. Log frames/speed/wrap/blend and record complete video of head/shoulders/feet/dress. Normal procedural layers remain active. | Skeleton distortion, floor drift, overwritten request, unexpected root travel, or failure to end at five seconds |
| D: resume | After one cycle, confirm normal idle resumes. Then walk/stop, aim/release, reload and perform a safe interaction; compare binding logs and visuals with baseline. A movement/aim request during playback must cancel the test normally; abort rather than forcing completion. | Any protected action fails, attachments change, or original controller ownership does not resume |
| E: rollback | Stop/discard the harness, close RE9, remove only the new experiment MOTLIST, and restart from the same existing scene. Confirm original idle and protected actions plus loose-file absence; recheck character/source hashes. | Original behavior or installed baseline differs |

If no decoded-pose API exists, B and C need a separately authorized combined
isolated playback/pose measurement to establish decoder behavior. They remain
separate pass criteria. A method to sample resource-only transforms is not
invented. Do not progress from A on a parse-only claim.

Compare native offline reference frames including the full-track W-zero crossing;
decompose procedural/IK effects before assigning runtime differences to encoding.
If only composed world joints are exposed, compare the same captured layer
configuration and label procedural contributions. Report unavailable raw local
transforms. Do not claim sub-micrometre runtime accuracy from visual evidence.

**Deactivation:** the future harness must restore its exact layer/bank state
using verified APIs and relinquish all temporary ownership. If deregistration
or cache behavior is unknown, process exit is the reliable full reset. Do not
hot-delete a loaded resource or blindly clear global caches. **Rollback:** remove
the one newly added file after exit and relaunch; no official PAK, character mod,
controller or save restoration should be necessary. If the character package
was changed independently, reinstall the preserved standalone v0.1.2 package
through the established method; do not mix partial old release files.

## Offline validation and reproducibility

The Stage 1 suite includes Lua 5.4 execution via pinned Lupa 2.6, an explicitly
mocked SDK, read-only call auditing, missing/incorrect/static API signatures,
sample limits, duplicate load and capture gating. These tests validate script
behavior under the fixture, not RE9 API availability, live overhead or playback.
Existing 57 tests are retained. JMAP masks are independently decoded by pinned
ReeLib. Both native candidate files are copied byte-identically from accepted C;
no new compression or retargeting is performed.

Reproduce from the project folder (owned extracts and pinned local tools needed):

```powershell
$projectPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $projectPython -m pip install --target tools/runtime-probe-deps lupa==2.6
& tools/dotnet10/dotnet.exe restore scripts/animation/ReeRuntimeInspect/ReeRuntimeInspect.csproj --locked-mode --packages tools/nuget
& tools/dotnet10/dotnet.exe build scripts/animation/ReeRuntimeInspect/ReeRuntimeInspect.csproj --no-restore -c Release
& $projectPython scripts/runtime_stage1.py --prepare
& $projectPython -m unittest discover -s tests -v
& $projectPython scripts/runtime_stage1.py --verify-environment
& $projectPython scripts/runtime_stage1_finalize.py
```

An existing before-snapshot is not silently updated if the protected installed
environment changes. Legitimate game-save/autosave or mod changes after user
testing must be reviewed and recorded as a new environment checkpoint. A fresh
game build requires a new diagnostic/build comparison; do not reinterpret the
current identifiers as permanent support.

## Sources and evidence classification

* [Pinned REFramework SDK bindings](https://github.com/praydog/REFramework/blob/d1461375aee4ec3f313170f8eaad12064eb542d9/src/mods/bindings/Sdk.cpp): verified local reflection API, method signatures, SystemArray/native-array getters.
* [Pinned ScriptRunner](https://github.com/praydog/REFramework/blob/d1461375aee4ec3f313170f8eaad12064eb542d9/src/mods/ScriptRunner.cpp): verified manual file-picker loading and callbacks.
* [Pinned JSON binding](https://github.com/praydog/REFramework/blob/d1461375aee4ec3f313170f8eaad12064eb542d9/src/mods/bindings/Json.cpp): verified relative data-directory writes.
* [Pinned Object Explorer](https://github.com/praydog/REFramework/blob/d1461375aee4ec3f313170f8eaad12064eb542d9/src/mods/tools/ObjectExplorer.cpp): SDK dump and reflection inspection fallback.
* [EMV Engine source](https://github.com/alphazolam/EMV-Engine/blob/a8a89961fde640d542afc72bd66fd8e12f3b82b3/EMV%20Engine/reframework/autorun/EMV%20Engine/init.lua): documented older-game getter/dynamic-bank/invocation examples; RE9 availability unverified.
* [Pinned ReeLib JMAP reader](https://github.com/kagenocookie/RE-Engine-Lib/blob/ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef/REE-Lib/OtherFiles/JmapFile.cs): independently checked JMAP28 masks and auxiliary data.
* Accepted C reports and Stage 1 environment, extraction, mask, protection,
  SDK-source and test manifests: local numerical/byte evidence.

**Verified:** local build fingerprints, protected file identity, original static
banks/lists/controller records/JMAP masks, read-only script source and mock
behavior, candidate byte identity and prior native offline precision.
**Pending actual runtime evidence:** Grace body/FPS identity, active idle tuple,
layer/mask/transition/IK behavior, resource routing/cache, full-quaternion engine
support, five-second playback and gameplay restoration.
**Hypotheses:** component-local dynamic invocation is the lowest-scope viable
route; direct requests may be overwritten by the controller; conversion-map
mask values may differ from runtime deformation masks. None is an integration
compatibility claim.

The next action is the short read-only capture checklist above. Facial/blinking,
cloth physics, new geometry/weights and runtime activation remain outside this
stage.

