# Assembled alignment review — 9 October 2026

**Controlled first-test build accepted, with limitations.** The revised native-export assembly keeps tested skin/garment boundaries and limb attachments together. The previous large hem folds and pelvis exposure have been reduced enough for an experimental runtime test. Small creases, isolated cloth/body spots and deep-flexion artifacts remain; no native cloth simulation is present. Uncovered body cutouts remain intentional source segmentation.

The offline review uses portable Blender **4.3.2**, the saved `assets/work/BelaGrace_preparation.blend`, and geometry reopened from the staged RE9 binaries. The user confirmed GraceBun is disabled. The first runtime screenshot now confirms a standing front-oblique assembly with FreeCam enabled: no obvious large positional offsets or detached visible limbs. Exposed wrist strips are consistent with the intentional cuff segmentation. The neck is partly obscured and the dress hides leg joints/boots; those areas and dynamic gameplay remain unverified. Runtime evidence is recorded separately in `reports/runtime_test_01.json`; the offline review report retains its original scope.

The second runtime screenshot shows a bent-arm handgun pose with apparently aligned hands/grip and no obvious large wrist, sleeve or shoulder detachment. The user reports weapon physics look correct; observation and limits are in `reports/runtime_test_02.json`. This supports the hand/weapon mapping for the shown pose. Locomotion, crouching, covered lower-body joints and specific weapon sequences still require evidence. Intentional exposed wrist strips are not classified as positional errors.

| Region | Current observed result | Evidence and limits |
|---|---|---|
| Neck seam | No obvious opening in rest/head-turn renders | Source-aware audit follows 92 originally coincident cross-submesh skin groups; maximum separation 1.358 mm in all six numeric fixtures. No automatic welding or general hole detection |
| Shoulders | Sleeves and exposed torso remain attached in the tested arm pose | Front/oblique rendered view; limited range and no imported game animation |
| Elbows | Skin/sleeves bend without an obvious detached segment | Unilateral and bilateral flexion; broader motion/twist coverage pending |
| Wrists | Gloves stay at the wrists during the tested hand rotations | Exposed skin strips at cuffs remain; do not classify these as gaps from object boundaries alone. Weapon grip untested |
| Pelvis | Rest/step/rear views retain coverage after up to 25 mm radial garment clearance | Broader whole-skirt fields and smoothing alone were rejected for exposing stockings. The accepted fit preserves pelvis weights before lower-field diffusion |
| Knees | Stocking limbs bend and remain covered in the dressed step/bilateral-flex fixtures | Lower-skirt field removes hem foot/toe influences; 40 diffusion steps reduce abrupt transitions. Residual creases and small cloth/body spots remain |
| Ankles | Original Grace boots surround the stockings in the rest and step inspection views | Original boot weights and sole plane retained. Bela heels are omitted. Floor contact, collision and game IK untested |

All **14** current images under `reports/alignment/` were reviewed: the original eight neck/arm/step/ankle fixtures plus rear step, rear bilateral flexion, side/rear deep crouch, stride and leg abduction. Exact names are in `reports/alignment_review.json`. The full rear rest assembly is in `reports/preview_rear.png`. Diagnostic uncovered images intentionally hide clothing; they are not the final outfit appearance. Deep crouch reveals calves below the raised open rear hem; this is different from body piercing the cloth. Game floor contact remains untested.

The numerical skin report is `reports/assembled_seam_audit.json`. The garment audit (`reports/garment_seam_audit.json`) follows **1,450 exported rest-coincident groups** through all 14 poses; their maximum measured spread is zero. Both use a **2 mm review threshold**, chosen for this offline audit, not a Capcom tolerance. These checks establish limited continuity, not general hole detection, collision-free cloth, facial deformation, heel correctness, shader behaviour or runtime skeleton binding.



The rest correction is explicit: Dress/DressBack vertices receive up to **25 mm** radial clearance in a faded pelvis band. The retained source surface-transfer sidecar separates original geometry fitting weights from new runtime weights. Topology is preserved; no geometry welding is performed. `reports/geometry_revision_audit.json` proves other geometry and Grace's bind matrices are unchanged. Earlier weight-only reports precede this clearance revision and are not a description of the current mesh positions.

Next: continue movement, weapon and crouching checks in [FIRST_TEST.md](FIRST_TEST.md), then repair observed runtime failures before expanding fidelity. A standing screenshot does not establish successful playable functionality. Rejected broad fields, smoothing-only candidates, heel compression and older skirt-fit images remain diagnostic history.

The ADS screenshot confirms actual hair/hood penetration. A separate hair-weight candidate reproduces and reduces it in eight synthetic head/chest fixtures, including reopened native files; [HEADWEAR.md](HEADWEAR.md) records its limits. A cutscene close-up is reported visually correct with lighting, while facial motion remains absent. [Runtime results](RUNTIME_TESTS.md) distinguish this from offline evidence.

