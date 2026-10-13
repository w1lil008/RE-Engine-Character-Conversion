# Milestone D: offline hardening and live discovery

Accepted checkpoint 48d139f and all earlier accepted packages, source/retarget
references, native C outputs, and D1 sources/reports remain protected. New tools
and evidence are separate. No converted animation has been installed, loaded,
registered or played. After explicit authorization the agent launched RE9, loaded
existing save 4 (Guard Office / Standard Classic), ran the read-only probe,
saved unique captures and released Lua references. The first session closed
normally. After the second capture, the graphical tool stopped reliably updating
the game or confirming exit; RE9 may still be open. No forced termination or
restart was attempted. Close it normally when returning, before another capture.

## Results and evidence

The current evidence is under `reports/runtime_preparation_v0.2.0/`. The final
test count and package checksum are recorded in `phase_results.json` and
`automated_tests.json`. The complete test log is `automated_tests.log`.

A fresh native conversion in
`build/animation_v0.2.0/native_runtime_hardening_verify_2/` reproduces both accepted
native files byte-for-byte. The original 211-motion/270-slot bank again passes
the complete unchanged roundtrip. The 601 sampled poses over 611 joints retain
the maximum positional error of **0.144352 micrometres**, quaternion continuity,
target limb translations, suppressed accumulated root motion and accepted
millimetre foot sway. This is offline validation, not engine playback evidence.

Pinned ReeLib independently agrees with the new Python reader on all **3,929
node identities/names/parents/attributes** and **3,687 state edges** across nine
MOTFSM2.45/BHVT42 controllers. All state-edge targets and transition-map references
resolve locally; there are still **577** unique transition data records. Full
graphs are local build diagnostics rather than huge distributable reports.

Verified examples in `tpsbase` include:

| Source → target | Map ID | Condition token | Transition record index |
|---|---:|---:|---:|
| root/Idle/new state 6DD29B56 → root/Idle/WalkEnd | 617970910 | 68 | 2 |
| root/Idle/WalkEnd → root/Idle/new state 6DD29B56 | 1818684153 | 70 | 2 |
| root/Idle/new state 6DD29B56 → root/Idle/IdleTurn | 3267045132 | 69 | 2 |

Upper-controller graphs connect HoldStart equipment/hands/melee branches and
aim-inhibition branches. FPS base has HoldIdle standing/crouched transitions.
These are actual encoded graph relationships. Interpreting their labels as
neutral-idle/aim gameplay behaviour remains an inference: condition tokens and
typed RSZ action payloads are not decoded without a matching RE9 schema.
Common controllers also contain other character/context branches. A named leaf
is not proof of a loaded motion, active bank, or safe replacement slot.

## User-assisted live discovery

The first D2 user screenshot showed zero selected objects. D3 discovery capture
`20261010T173443Z_0.json` proved game **re9**, framework
**d1461375aee4ec3f313170f8eaad12064eb542d9**, TDB **83**, and a static
zero-argument `via.SceneManager.get_CurrentScene` returning `via.Scene`.
The original probe incorrectly required that particular getter to be an
instance method; D4 fixes its dispatch guard through the supported SDK adapter.

D4 capture `20261010T173843Z_0.json` proves scene discovery works and returns
**417** motion components. Its previous 256-component cap was insufficient.
It also reflects `Motion.getLayer(uint) → via.motion.TreeLayer`,
`getDynamicMotionBank(int) → via.motion.DynamicMotionBank`, and the following
setters **without invoking them**:

- Motion.setDynamicMotionBankCount(int).
- Motion.setDynamicMotionBank(int, via.motion.DynamicMotionBank).
- DynamicMotionBank.set_MotionList(via.motion.MotionListResourceHolder).
- DynamicMotionBank.set_BankID(uint).
- DynamicMotionBank.set_OverwriteBankID(bool).

Those captures are preserved as raw references with SHA-256 records and strict
analysis reports. Reflection proves availability/signatures, not successful
registration or correct lifetime/rollback semantics.

D5 scans up to 2,048 components with a bounded getter budget and hides unrelated
objects in the UI. It no longer depends on the older `get_ActiveMotionBank` API,
which was absent from the observed Motion definition. It records the motion-bank
asset and ID tables where exposed, plus dynamic banks and reflected wrapped-array
accessors. Automatic selection is conservative and still requires user confirmation.

The user's screenshot identifies the Grace prefab candidate **cp_A100**, entry
412, with an animation-component joint count of **80**. Several separate Shadow
and numbered render objects report 611 joints. The mesh's accepted 611-bone rig
has not changed. Do not assume the 80 reported controller joints and 611 mesh
joints form interchangeable animation hierarchies: their association requires
the live component/layer/joint-map evidence. Actual idle bank/motion selection
is now partially established from real captures; exact switch/resource routing and
controller/rendered-rig association remain separate gaps.

## Probe and analyzer behaviour

Use `scripts/runtime/bela_binding_probe_v7.lua`; v2–v6 are retained to explain
the user's earlier diagnostic attempts. The accepted D1 probe is unchanged.
The [quickstart](RUNTIME_CAPTURE_QUICKSTART.md) contains the exact manual steps.

All engine method calls use a read-only getter whitelist and verified reflection
arity/static/parameter checks. The one native scene getter is separately checked
against its observed signature. No hooks, setters, raw-memory writes, resource
creation, bank registration, playback requests or manual refcount changes exist
in the probe. Integration setter signatures are collected as metadata only.

Sampling is nominally 5 Hz, capped at 600 samples/120 seconds, four selected
objects, sixteen layers and sixteen nodes per layer, 2,500 getter calls per sample,
100 errors and 256 markers. Missing node counts are reported; node zero is not
guessed. Null bank/layer indices remain explicit. Helper/FSM/weapon/IK fields
are observed only where reflected on selected components. Performance and
getter coverage are evidenced by the saved live captures; mock tests remain a
separate validation stage.

Pinned REFramework JSON implementation returns true even if its stream write
fails. D5 verifies matching four-space serialization against both `fs.read` and
`json.load_file`. It checks filenames including corrupt existing JSON, keeps
failed captures for retry, and avoids duplicate callbacks and duplicate saves.
The SDK has no exclusive-create primitive here; collision handling assumes one
active writer for the diagnostic folder. `fs.glob` scans the data folder only
when saving, not during every sample.

`runtime_capture.py` validates v1/v2 schemas, nullable SDK empty arrays, object
identity, unsigned IDs, resource paths, sample ordering, duplicates, bounded
counts and finite values. It reports observed motion/state changes, possible
loop/restart boundaries, bank ambiguity, missing fields, API failures, helper
changes and idle candidates with marked walk/aim returns. It preserves observed
versus inferred scope and never authorizes activation. Duplicate JSON keys,
nonfinite literals and captures above 64 MiB fail validation.

`runtime_collect.py` reads only JSON inside the Bela diagnostic directory,
preserves a raw workspace reference, and produces a separate analysis. Repeated
analysis cannot silently replace different prior evidence.

## Integration recommendation and unresolved dependencies

Prefer a fresh MOTLIST resource path and a new component-local dynamic bank,
subject to the captured player/layer, holder API, ownership and recovery checks.
No runtime bank ID or controller slot has been invented. The inert package is
`dist/BelaGrace_RuntimePreparation_0.2.0_OfflineHardened.zip`;
its unpacked copy is `build/animation_v0.2.0/runtime_hardening/preparation/`.
It has no native game directory layout, modinfo, autorun, installer or playback
harness. Extract to a workspace only. Its two native resources are accepted C
bytes under `resources/`; the standalone MOT is for inspection. The MOTLIST
contains its motion and requires no separate loose MOT copy.

Future resource path: `Animation/bela_prototype/v020/bela_idle.motlist`.
Future single loose file, after separate authorization:
`natives/stm/animation/bela_prototype/v020/bela_idle.motlist.1047`.
The retained jmap reference is
`GameAssets/Character/CharacterPrefab/cp_A1/cp_A100/JointMap/cp_A1JointMap_ForConvert.jmap`.
Descriptor motion 0/switch 0 are prototype-local identifiers, not Grace's live idle.

The pinned EMV example creates a resource holder using a raw pointer write at
0x10. That implementation is not reused. Pinned REFramework exposes
`REResource.create_holder`/`create_holder_global`, backed by a ResourceHolder type
check and SDK-managed object construction. The observed MotionListResourceHolder
type and setter parameter agree with the intended route. Native resource typeinfo,
loader scanning/readiness, holder lifetime and actual registration success remain
unverified. A successful parse or existing exported API does not establish these.

The live framework startup log reports `LooseFileLoader` failures locating
`via.io.file` and the `path_to_hash` function. Therefore the fresh loose MOTLIST
path is a proposed path, not a proven load route. Working character rendering
does not establish fresh animation-resource lookup. Verify a supported resource
overlay mechanism before any authorized load test; do not update framework
components, change configuration or choose a fallback replacement silently.

The future harness must append a fresh bank without replacing existing entries,
record original count/entries and exact object/layer identity, verify an unused
bank ID, and have a tested original-controller resume path. Never force puppet
modes, change masks, or repeatedly request play to fight the FSM. If a one-shot
request is overwritten immediately, abort and investigate layer ownership.

Fallback: a one-slot MOTLIST overlay only after live binding is established.
It needs alias/rest-table/index/event preservation and timing analysis; an
one-frame base idle plus separate long additive motion cannot blindly receive a
300-frame full-body clip. The 814-frame/90-event GeneralM caution clip used in C
was a roundtrip fixture, not the observed base idle. No fallback slot/package is prepared as a
working replacement at this stage.

## First future experiment: separate A–E gates

1. **A / load:** verify build/framework/native hashes, fresh path and clean
   conflict preview. Load the one-MOT resource without playback; log null resource,
   holder mismatch, loader errors and timeout. No bank registration after a failure.
2. **B / decoding:** retain full XYZW on **R_Arm_Clavicle** and **L_Leg_Upper**.
   Both offline parsers accept these tracks; engine support is unknown. If a native
   clip sampler exists, compare 301 keys plus 300 half-frame poses before live
   layer/procedural/IK blending, using 50 µm position / 0.05° rotation gates.
   Rendered IK-adjusted joints alone cannot prove codec accuracy. If no sampler
   is available, disclose that gap and seek authorization for combined B/C visual
   testing; do not claim numerical engine decoding or approximate the tracks.
3. **C / play:** one five-second, 0–300 frame, 60-FPS cycle in a verified
   non-critical layer/state. Original gameplay remains in control. No permanent
   idle swap, indefinite loop, accumulated root travel or per-frame forced requests.
4. **D / preservation:** confirm idle resumes and walking, aiming, reloading and
   interactions interrupt cleanly. Inspect shoulder/thigh quaternion motion,
   weapon/IK behaviour, head/hood follow, dress and feet against accepted previews.
5. **E / rollback:** exit RE9 completely; hash-check ownership and remove only
   the newly added loose MOTLIST, leave all pre-existing directories/configs intact,
   restart with the normal mod and confirm original behaviour. Process exit also
   discards temporary component banks and cached resources.

Immediate visual disable requires a verified resume/abort path; process exit is
the reliable recovery fallback. File deletion while RE9 is running is not proof
of cache unload. No executable playback harness is generated until those gates
can be bound to the actual player/layer/API evidence.

## Protection and practical limits

`runtime_preparation_protection.py` adds accepted D1 source/report/package checks
to all A/B/C/v0.1 hash gates. Preflight rechecks 90 recorded installed files,
Steam build **23634047**, executable **1.3.1.0**, saves and official archive size/
mtime. Official PAK content is not newly hashed in this phase. Unrelated mod
archives/configurations are neither altered nor proven universally conflict-free.
The candidate destination and `pak_mods` inventory are checked; unknown archives
remain opaque. No installer or removal tool exists in the preview script.

The initial preflight passed with RE9 closed. Subsequent ordinary gameplay
may write saves or framework UI settings. Differences are recorded read-only,
never automatically restored. The final save fingerprints differ from the
original D1 snapshot; this does not identify which ordinary gameplay session
caused those changes. No direct save edits or manual saving occurred during the
agent captures. All 90 protected installed file hashes still match, and official
PAK sizes/mtimes match. v0.1.3 still needs its own explicit runtime
acceptance; viewing Bela here does not complete its entire checklist.

Remaining work before playback: repeat the marked sequence with the complete v7 node/FSM coverage;
establish controller versus rendered skeleton association, active bank/list/type/
switch/mask/layer, actual one-shot/abort semantics and cache/lifetime handling;
then prepare the concrete harness for separate authorization. Facial animation,
blinking, lip-sync and cloth physics are outside this task.

## Live binding results (10 October)

`live_binding_evidence.json` retains capture paths, hashes, observed tuples,
static name matches and scope limitations. Your 130-sample atrium capture
contains idle/walk/idle/aim/idle plus reload. Its four-node cap omitted some
of the twelve nodes blended during walking; v6/v7 raises the cap to sixteen.
The autonomous v6 Guard Office capture collected **574** samples in the bounded
120-second window, **13 ms** peak, no API errors or truncation. It read seventeen
merged bank IDs with the exact reflected `System.UInt32[].Get(Int32) -> UInt32`;
no primitive values were mistaken for object pointers. v7 adds the exact
reflected `MotionFsm2.getCurrentNodeID/Name/NameHash(UInt32)` getters per actual
FSM layer and reads its resource holder. The loaded source and capture hashes
are retained alongside the screenshots and framework log snapshot.

The autonomous v7 capture contains **125 samples**, 13 ms peak, no API errors
and no truncation. Together with the user and v6 captures, there are **829**
preserved samples. The following resource strings and current states are live
getter results, corroborated against the static graph by resource path, complete
hierarchy, numeric ID and name hash:

| FSM layer | Loaded TPS controller | Current node | ID | Name hash |
|---:|---|---|---:|---:|
| 0 | TPSBase.motfsm2 | Idle.new state 6DD29B56.Idle | 1962794700 | 3389212796 |
| 3 | TPSUpper.motfsm2 | UseBaseLayer.IsForceUseBaseLayer | 255807882 | 1281605410 |
| 3 | TPSUpper.motfsm2 | Emote.Normal | 1749198731 | 1948795948 |
| 5 | TPSLeftUpper.motfsm2 | UseBaseLayer | 1936531262 | 4170644924 |
| 8 | TPSAdd.motfsm2 | Default.NormalBreath | 1565925381 | 4197116285 |
| 8 | TPSAdd.motfsm2 | Default.Empty | 1094006591 | 574382652 |

The common resource directory is
`AppSystem/Character/CharacterPrefab/PlayerCommon/Subtype/TPS/MotionFsm/`.
TPSUpper Emote.Normal and TPSAdd Empty were observed during the ordinary
look-at-watch gesture. Labels do not decode transition conditions. FSM-layer
indices and motion-tree indices are recorded separately; corresponding indices
do not establish interchangeable mask or ownership semantics. The current ID
is retained as an exact decimal string. Shared FPS/TPS IDs are disambiguated
by the observed controller resource, rather than name or hash alone.

The exact loaded v7 source is retained as
`build/animation_v0.2.0/runtime_hardening/live_evidence/20261010_v7_loaded_d898cfec.lua`.
Only two UI strings were subsequently corrected: the title encoding and its
verification-status text. No engine-call or capture logic changed. The execution
record retains both hashes and the exact scope of this cosmetic difference.

| Context | Actual observed motion | Layer / bank / ID | Mask | Static corroboration |
|---|---|---|---:|---|
| Atrium, Requiem (user) | GeneralS_0001_Idle_Loop_VerB | 0 / 0 / 1 | 0 | GeneralS slot 1, one frame, static switch 0 |
| Atrium, Requiem (user) | GeneralS_6040_idle_Loop_Add_VerA | 8 / 0 / 6040 | 1100 | GeneralS slot 213, 1,136 frames |
| Guard Office, holstered (agent) | GeneralM_0001_Idle_Loop_VerB | 0 / 0 / 1 | 0 | GeneralM slot 1, one frame, static switch 0 |
| Guard Office, holstered (agent) | GeneralM_6040_idle_Loop_Add_VerA | 8 / 0 / 6040 | 1100 | GeneralM slot 213, 666 frames |

All names above have the `ch0200_` prefix. The actual Motion bank holder names
`Animation/ch/ch02/ch0200/motbank/ch0200.motbank`. The Guard Office capture also
observes chamber-clear, holster and look-at-watch motions without gameplay input.
TargetBankType is 4097 (0x1001), compared with 1048833 (0x100101) in the Requiem
capture. Motion node type is 0 in the Guard Office; tree-layer type/local type
is -1. These values are reported as exposed, not treated as a verified dispatch
formula. The same bank 0 / motion 1 changes full motion name/resource identity;
the analyzer now detects that change explicitly. ResourceDataLongId happens to
be sixteen times ResourceDataId in this capture; its semantics are **not**
assumed to be a switch, hash or stable identifier across sessions.

The three dynamic bank entries returned null through both exposed accessor
routes. That does not prove empty/free slots or permit overwriting them.
Static MOTLIST switch 0 is corroborating file metadata, not an observed live
switch. Original jmap masks, runtime layer masks and helper/IK effects are
separate facts. No first-person capture or native resource load occurred.

The graphical automation API reliably operated menus and REFramework widgets,
but lacks held-key/right-button controls; brief game-input presses did not
reliably register. No injected inputs, settings workaround or blind movement
sequence was used. When you return, run the short v7 sequence in the quickstart
to obtain all blended nodes, indexed FSM states and the same weapon context.
This is the remaining manual action; it does not require a prototype mod package.

