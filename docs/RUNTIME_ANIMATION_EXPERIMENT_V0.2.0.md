# Milestone D: validated native playback prototype

The approved Bela idle loaded, decoded and visibly played on the existing Grace-based Bela character in RE9. A measured single cycle lasted **5.009 seconds**. The harness detached its own layer and bank, verified the original references and counts, and observed the original idle for another five seconds. All temporary animation files have subsequently been removed with RE9 closed.

This is a successful isolated runtime proof. It is not a persistent idle replacement or approval of all gameplay, first-person, cutscene, weapon, foot or garment behavior. v0.1.3's full runtime checklist remains pending.

## Target and accepted inputs

- Branch: `codex/v0.2.0-source-animation`; prior checkpoint `c4b155660d2d82ba6fe73fef671190ff1aec116a`.
- RE9 Steam app 3764200, installed and target build 23634047; executable 1.3.1.0, SHA256 `9742b40b5a177cee95015714488fe7bdddbe5348892033b4c807d823a20ee168`.
- REFramework `d1461375aee4ec3f313170f8eaad12064eb542d9`, TDB 83; existing LooseFileLoader enabled. No REFramework replacement, configuration edit or new plugin was required.
- Accepted source A `44eb9e1`, retarget B `e579c25`, native C `91ee9fe`, runtime preparation D1 `48d139f`. Their files and release packages remain protected.
- Native resource: `build/animation_v0.2.0/native_idle_canonical/native/bela_idle.motlist.1047`; SHA256 `48505359a3dd5411dc98582649964cce07c10a7114229d0a60db96dd5467c477`. The MOT 983 is embedded in this MOTLIST 1047, so only the MOTLIST was staged.
- Five seconds, 301 keys, native frames 0–300 at 60 FPS, 24 rotation tracks and the accepted root translation. No root motion was added or channels approximated.

## Verified live binding

The playable controller is **cp_A100's 80-joint `via.motion.Motion`**. The 611-joint meshes are its render siblings, rather than the controller to which a bank should be attached. Both visible 40/20 renderers expose explicit constraints from every one of the 24 animated joints to the matching cp_A100 joint. Captured constrained world position and quaternion differences were zero. This verifies the animated subset, not a complete 611-joint correspondence.

The live joint-map holder is `GameAssets/Character/CharacterPrefab/cp_A1/cp_A100/JointMap/cp_A1JointMap.jmap`. The earlier offline `ForConvert` map is a different resource.

In the quiet Main Care Centre atrium, third person, holding Requiem:

| Item | Observed value |
| --- | --- |
| Existing tree layers | 9, indices 0–8 |
| Existing dynamic bank slots | 3; all null before and after the experiment |
| Base idle | Layer 0, bank 0, motion 1, joint mask 0, enabled, weight 1 |
| Base idle motion name | `ch0200_GeneralS_0001_Idle_Loop_VerB` |
| TPSBase FSM idle node | ID 1962794700, name hash 3389212796; `Idle.new state 6DD29B56.Idle` |
| Layer 3 | Bank 10, motion 5000 |
| Layer 4 | Bank 100, motion 6000, mask 201 |
| Layer 8 | Bank 0, motion 6040, mask 1100; additive breath |
| TPSAdd FSM | `Default.NormalBreath`, ID 1565925381, name hash 4197116285 |
| Motion bank asset | `ch0200.motbank`; GeneralM/GeneralS/Requiem resource candidates observed elsewhere in preparation |

Seventeen enumerated bank IDs must not be confused with seventeen playable tree layers. Base idle's live motion name is verified; its exact active MOTLIST path and switch value were not exposed by the sampled getters. Static names, the 3,929 named nodes, 3,687 edges and 577 transition records do not fill that gap. No original file slot was selected for replacement. FPS equivalence remains unverified.

## Load and decode gates

1. An SDK resource handle and holder alone did not establish readiness. Ownerless Motion initialization failed earlier investigation; that route is rejected. A new owned scene object with a Motion component provided the required component context. Original Grace motion served as the control arm.
2. MotionInfo resolved the exact expected name, ending frame and tracks before any character playback. `getAnimationTransform(UInt32, Single, AnimationTransformData)` was checked through exact reflected signatures. Result containers were new owned objects; sampling did not apply poses to the character.
3. The engine decoded **14,424 Bela samples: 24 tracks × 601 half-frame times**, plus 340 samples of the 68-track unchanged Grace control.
4. Bela's maximum raw-channel rotation error was **0.000027107°**; root-channel position error **0.001041 micrometres**; quaternion norm error **1.394e-7**. Original Grace control: **0.000281233°**, **0.129774 micrometres**. Both arms passed explicit tolerances.
5. Both full XYZW tracks passed actual native engine decoding: `R_Arm_Clavicle` and `L_Leg_Upper`. They were neither removed nor approximated.

These are live engine observations, not results from a second offline parser. `reports/runtime_experiment_v0.2.0/engine_channel_comparison_corrected.json` contains thresholds, provenance and per-track results. The failed earlier comparison remains preserved: Lua integer frame arguments had been passed to a Single parameter; using explicit floating-point arguments corrected the call, without modifying the native file.

## Invocation and resource lifetime

The verified mechanism is a **component-local DynamicMotionBank plus a new appended TreeLayer**. It requires no controller asset edits, bank-file registration, original motion replacement or PAK changes.

The new resource uses the isolated path `Animation/bela_prototype/v020/engine_decode_20261011_c/bela_idle.motlist`. Bank 65000, motion 0, switch argument 0 first had to fail lookup, ensuring it did not already resolve on this component. The harness then created a holder and DynamicMotionBank, appended slot 3, called `setupMotionBank`, and verified the exact Bela MotionInfo. A new layer at index 9 used base layer 0's blend mode and joint mask 0.

Before this, a separate owned scene validated layer grow/shrink behavior, reference preservation and cleanup. The live Grace dry run then advanced the candidate at **zero weight**, resolved all 24 joints, and restored nine layers and three slots. Playback was authorized only after that gate passed.

Resource loading uses the pinned SDK's `create_resource` / `create_holder_global` bridge. Its native lifetime fallback was checked against the protected EXE's release routine and pinned ResourceManager source; no guessed process offsets or arbitrary process-memory writes were introduced. Owned holders are retained while bound. Cleanup disables and clears the owned layer, shrinks the layer array, removes the appended bank, rebuilds bank binding, verifies every original reference, and then releases Lua references. If detachment fails, the script reports `CLEANUP_FAILED` and retains holders instead of releasing a still-bound resource.

`get_Setuped` was an observed transient update pulse, not a stable readiness flag. Readiness requires the actual resource name, advancing time, ending frame, zero weight and all joint lookups.

## Actual playback and visual evidence

`grace_one_cycle_20261011_b` passed the strict analyzer with zero runtime errors. It recorded 22 dry-run poses and **82 visible poses**, covering frames **3.698910–298.644775**. Native looping was observed; the harness detached at the first wrap, after 5.009 seconds, with about 0.599 frame already into the wrap. It did not intentionally request a second cycle.

All 24 live weight-one layer rotations were compared at their recorded native times. Maximum difference: **0.000024686°**. Full XYZW results: clavicle **0.000006613°**, left upper leg **0.000002415°**. These certify layer rotations, not final controller or skinned vertex transforms.

Eight synchronized screenshots cover the normal pose, Bela playback posture and restoration, at roughly 1.13-second intervals. The visible rear/upper-body view showed the lowered-arm Bela posture and subtle idle movement, then the original Requiem posture. No major hood or shoulder failure was apparent in those views. Feet and front-face behavior were not covered. This is a timestamped screenshot sequence, not a continuous 60 FPS video or user visual acceptance.

- `reports/runtime_experiment_v0.2.0/one_cycle_b_0.png` — before.
- `one_cycle_b_1.png` through `one_cycle_b_5.png` — playback.
- `one_cycle_b_6.png` and `one_cycle_b_7.png` — restored.
- `one_cycle_b_screenshots.json` — capture timing.
- `live_applied_rotation_comparison.json` — sampled live/native comparison.
- `grace_one_cycle_20261011_b_analysis.json` — strict result and every raw-capture hash.

The first visible cycle, session A, returned to normal successfully but had no playback poses in its saved array: countdown samples consumed the budget. Its analysis remains **FAILED**. The corrected run reserved the budget for actual playback and passed. Both runs and their frozen code are retained; the successful run is not used to rewrite the failed evidence.

## Root, gameplay and remaining constraints

The engine's raw root channel matches the approved native data. During playback, `TreeLayer.getLocalPosition(root)` instead reported y=0 and an XZ span of about **3.251 mm**. The native root channel's y is −7.173 mm. Root extraction and procedural composition have not been isolated, so that layer result is not evidence of world-space movement or a measured live foot drift. The separate post-restoration probe observed root mode enum value 2 and zero root translations; it did not observe extraction during Bela playback.

The original idle/bank/layer references resumed and remained valid for five seconds. A normal right-mouse aiming tap showed the aim reticle and raised weapon, followed by normal idle. The keyboard automation produced taps rather than reliable held movement; the captured base binding remained idle. The aim tap happened after the post-restoration JSON capture ended. Sustained walking/aiming, reload, interaction, FPS, cutscenes, weapon grip during Bela playback and world-space feet remain open. There was no crash during the successful decode, dry-run or playback sessions. An earlier unrelated load failure/crash was preserved and investigated; its cause is not asserted from nearby symbols.

After the successful live run, the reusable harness was additionally hardened to stop on a changed bank/motion/enabled/mask signature on **any original layer**, including an upper-body layer, and to leave legitimate incoming gameplay states intact. Those additional interruption branches and the improved manual-stop error path have offline coverage; they have not yet been exercised through sustained live input. The frozen successful runtime code remains unchanged.

| Risk / next feature | Complexity | Required evidence |
| --- | --- | --- |
| Native XYZW decoding | Resolved on pinned build | Retest after game/framework changes |
| Component-local loading and lifecycle | Verified in tested context | Retest scene changes and repeated launch/teardown |
| Final root and foot placement | High | World-space controller and renderer foot samples during playback |
| Smooth entry/exit and input interruption | High | Held walk/aim, reload and interaction tests, with original FSM/layer signatures |
| FPS and cutscene compatibility | Research-dependent | Separate live bindings and camera-specific masks |
| Weapon/IK composition | High | Final helper/hand transforms and visible grip during playback |
| Persistent selective idle behavior | High | Verified context guards and safe blending; no global file replacement |

## Reusable procedure and rollback

Main workflow: `scripts/runtime_one_cycle.py`. It previews staging, checks protected assets and pinned build identifiers, stages only a new hash-matched file with an ownership record, freezes a uniquely named session, collects evidence without overwriting it, and provides closed-game ownership-checked rollback. Lua handles the bank, layer, timing, gates and cleanup automatically. The user need not select banks or coordinate controller setup.

For a future repeat in this workspace, with RE9 closed:

```powershell
$projectPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $projectPython scripts/runtime_one_cycle.py preview_resource --session replay_20261011_01
& $projectPython scripts/runtime_one_cycle.py stage_resource --session replay_20261011_01
& $projectPython scripts/runtime_one_cycle.py prepare --session replay_20261011_01 --mode one_cycle
```

Review the preview before the explicit stage command. No existing destination can be overwritten. The generated entry is `build/animation_v0.2.0/runtime_experiment/replay_20261011_01/run_test.lua`. Launch the existing game, load the quiet Grace save, then choose this one file in **REFramework → ScriptRunner → Run script**. Close the REFramework menu during the twelve-second countdown. Leave gameplay idle. The harness performs the zero-weight check, one cycle, detachment and five-second restoration check itself. A `dry_run` session can be prepared instead to request no visible playback. Use new session names for each frozen preparation.

Afterward collect evidence, close RE9 normally and remove only the owned file:

```powershell
& $projectPython scripts/runtime_one_cycle.py collect --session replay_20261011_01
& $projectPython scripts/runtime_one_cycle.py rollback_resource --session replay_20261011_01
```

Rollback refuses while RE9 runs or if the owned file hash differs. It deletes one checked experimental file and no directories, original assets, configurations or saves. Normal game exit discards runtime components and cached references. If cleanup reports failure, stop gameplay, preserve logs and exit normally before attempting file rollback; do not reset scripts while a holder is bound or repeatedly restart a failing operation.

Runtime JSON: `<RE9_INSTALL_DIR>/reframework/data/bela_runtime_test/`. Frozen copies and logs: `build/animation_v0.2.0/runtime_experiment/<session>/`. Successful cycle capture: `grace_one_cycle_20261011_b_9.json` (SHA256 `1c0134e1dca6d8e6e9abb6dcc951a869e0f0325ad98ade0a407217967522a196`).

## Preservation, tests and next experiment

`final_protection_and_rollback.json` verifies 90 previously protected installed files, 815 original local inputs, both 80-file v0.1.2/v0.1.3 packages and accepted A/B/C/D checkpoints. The 20 current preparation sources and accepted OfflineHardened package were checked separately. PAK verification is size/mtime, not a whole-archive content hash. Historical Steam save hashes and whole appmanifest hash already differed before these experiments; none was edited or restored by these tools. Current installed/target build IDs and protected EXE hash match. Steam can change LastPlayed during normal launches; the reusable gate verifies build identity instead of requiring that volatile file to be byte-identical.

The final automated results and log are in `reports/runtime_experiment_v0.2.0/automated_tests_release.json` and its referenced log. They cover protected assets, native reproducibility and roundtrip, bounded mock lifecycles, input interruption, ownership/conflicts, capture validation and actual captured engine/layer rotation comparisons. Offline tests are explicitly separate from live proof.

The next experiment should keep this component-local method and unchanged native clip: record final controller/renderer root and both feet in world space over one idle cycle, followed by a held movement or aiming interruption with a short fade-out. Require correct original-layer resumption, weapon/helper behavior and resource detachment. Do not ship automatic idle selection until these checks pass. No facial animation, blinking or cloth physics has been started.

