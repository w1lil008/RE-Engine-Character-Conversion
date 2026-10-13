# Project status — 10 October 2026

The current release is **v0.1.3 stabilization**, with all 80 native payloads
identical to accepted v0.1.2. New installation/runtime confirmation is pending.
The runtime baseline remains v0.1.2; its acceptance is not overwritten by the
creation of a new ZIP. The detailed current engineering record is
[STABILIZATION_V0.1.3.md](STABILIZATION_V0.1.3.md).

| Area | Current verification | Practical limit |
|---|---|---|
| Recovery | Accepted ZIP recovered and hash-verified; complete checkpoint and Git source commit | Prepared/game-derived inputs remain local |
| Source rebuild | 80 generated native files byte-identical to accepted v0.1.2 | Requires owned game extracts, pinned tools and accepted sidecars |
| Native package | 8 meshes, 31 MDF variants, 41 TEX files | Base Grace parts only |
| Skeleton | All 611 original Grace bones, hierarchy and bind matrices checked | Runtime controller/IK behaviour is not inferred from binds |
| Tests | 14 tests, zero native validation errors | Offline checks, not gameplay tests |
| Poses | 14 body + 14 headwear fixtures; 20 renders reviewed | Synthetic poses do not reproduce game clips |
| Skin/dress continuity | 92 skin groups within 1.36 mm; 1,450 dress groups coincident | Does not prove collision-free motion |
| Hair/hood | Accepted hood-follow weight correction preserved; geometry untouched | No native secondary motion; wider runtime coverage pending |
| Thigh/dress | Existing weight diffusion and bounded clearance preserved | Rigid folds/hem lift remain in strong offline poses |
| Face | Original eyelid controls and native neutral/closed eye poses located | Bela lid/lash controls are not mapped; morph import is broken in pinned tool |
| Gaze | L_Eye/R_Eye weights retained; user confirms eye movement | Independent of blinking |
| Gameplay/cutscenes | User confirms successful tested rendering, movement, aiming, cutscenes and weapon handling | Not every action, outfit or cutscene is covered |

The old README/status statements that v0.1.2 ADS testing was pending were stale.
Historical package-creation manifests correctly describe creation-time testing
status. Observation 06 and `reports/releases/0.1.2/runtime_acceptance.json`
record subsequent hair/hood acceptance; current hashes verify identity again.

Blinking and native cloth remain deferred without speculative payload changes.
The authorized source-animation phase has now reconstructed the original RE8
daughters idle on its original 368-bone assembled rig. All 173 native transform
channels and 2,824 keys decode; Blender and export/reimport pass 601 source
comparisons. The complete preview contains 300 frames at 60 FPS. An optional
Provocative clip also passes; its 3.37 m forward root travel requires a separate
gesture/locomotion decision. See
[source-animation engineering record](ANIMATION_SOURCE_V0.2.0.md) and
current phase results (local artifact omitted).

The user has visually accepted the original source reconstruction. Milestone B
now retargets that idle onto Grace's unchanged 611-bone rig: 24 mapped body
rotations plus root translation, original geometry/weights and all 587 unmapped
local controls retained. Both five-second 60 FPS previews and matching review
angles are available. The 39-test suite and export/reimport checks pass; lower
dress folds and millimetre foot motion are documented for manual acceptance.
See [offline retarget record](OFFLINE_RETARGET_V0.2.0.md).

The user accepted Milestone B at `e579c25`. Milestone C's separate native
body-animation prototype passes original-idle decoded-float roundtrip, complete
list byte-preservation, independent MOT/MOTLIST parsing and 611-joint motion
comparison. See [native engineering record](NATIVE_ANIMATION_V0.2.0.md) and
current native evidence (local artifact omitted).
No controller, active bank or installation was changed. Full XYZW support,
joint-map/helper semantics and actual state binding await Milestone D runtime
evidence and separate user authorization. The manual v0.1.3 runtime acceptance
checklist remains pending independently.

At checkpoint `48d139f`, Milestone D Stage 1 identified the local target as Steam build 23634047,
executable 1.3.1.0, REFramework d1461375/TDB83. Protected A/B/C and release
hashes pass. Original JMAP28 masks independently decode: 60 runtime-map groups,
four conversion-map groups, 12 extra joints each and no embedded IK-motion
definitions. A manual-load probe and inert preparation ZIP are ready for the
user's live idle/walk/aim capture. Actual bank/layer/motion/switch/mask selection
was then unverified; no runtime integration was activated. See
[Stage 1 report and instructions](RUNTIME_ANIMATION_STAGE1_V0.2.0.md).

Milestone D now has real read-only RE9 observations and a live-tested v7 probe.
The Grace controller is cp_A100 (80 reported controller joints), separate from
611-joint rendered siblings. Layer 0 bank 0 / motion 1 selects a one-frame base
idle; layer 8 bank 0 / motion 6040 supplies a separate additive idle. GeneralS
and GeneralM motion names differ with weapon context, so IDs alone do not select
an overlay slot. The marked user capture is retained; a repeat v7 walk/aim
capture is needed for all blended nodes and indexed controller states.
The actual TPSBase idle node is `Idle.new state 6DD29B56.Idle`, ID 1962794700;
TPSAdd runs `Default.NormalBreath`. Six observed states match the recovered
controller paths, IDs and hashes. The fresh animation loader remains unverified;
the framework log contains LooseFileLoader discovery failures.
See [live evidence and remaining gates](RUNTIME_PREPARATION_HARDENING_V0.2.0.md)
and [short capture instructions](RUNTIME_CAPTURE_QUICKSTART.md).
The new inert package is `dist/BelaGrace_RuntimePreparation_0.2.0_OfflineHardened.zip`.
No converted animation or bank has been installed or activated. Accepted
packages, source/retarget references and native output remain hash-protected;
v0.1.3's separate runtime acceptance remains pending.

