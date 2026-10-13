# Current scope — v0.1.3, 10 October 2026

The current task confirms successful tested gameplay/cutscene rendering,
movement, aiming, weapon handling and lighting/material appearance, and
provisionally accepts the hair/hood correction. This is user evidence, not a
new test performed by project tools. Observation 06 ties v0.1.2 ADS acceptance
to installed hashes; the current stage matches those hashes. v0.1.3 natives
are byte-identical, but its newly packaged installation has not been tested.
Use `docs/releases/0.1.3/MANUAL_TEST_CHECKLIST.txt` for explicit action/scene
coverage. Blinking remains absent. Historical entries retain their exact scope.

# Runtime observations — experimental v0.1.0 and v0.1.1

These are user-run tests, with screenshots preserved unaltered. They establish
the listed scope, not a blanket gameplay or all-cutscene pass. The installed
v0.1.1 build remains unchanged by project tools while the next candidate is prepared.

| Check | Current result | Evidence |
|---|---|---|
| Standing assembly | Bela face, hood, sleeves, gloves and dress render together; no obvious large offset in the supplied view | `reports/runtime_test_01.json`; standing screenshot; FreeCam enabled |
| Installed build identity | All 80 native files and the Fluffy ZIP matched delivery during observation 01 | Exact hashes in observation 01 |
| Weapon handling | User reports weapon physics look correct; bent-arm pistol grip looks aligned | `reports/runtime_test_02.json`; specific firing/reload/holster sequences not enumerated |
| Handgun ADS | Over-shoulder aiming view loads with weapon/arms visible | `reports/runtime_test_03.json` |
| Hair/hood during ADS | **Observed defect:** blond cards penetrate the right outer hood | Observation 03; actual intersection, not intentional mesh segmentation |
| v0.1.1 ADS retest | User reports "slightly less obvious, still there"; lower blond lock still penetrates the hood near the shoulder | `reports/runtime_test_05.json`; all 80 installed native files match v0.1.1 |
| One cutscene | User reports the scene looks correct and lighting is spot on; close-up shows Bela face/hood/hair/necklace | `reports/runtime_test_04.json`; exact scene/chapter not supplied |
| Facial animation | **Absent**, as the user confirms; expected current neutral-head limitation | Observation 04; no lip/eye/expression mapping has been implemented |
| Walking, turning, running, stairs | Pending | Need limb/dress motion and floor-contact results |
| Crouching and interactions | Pending | Need skirt/body/floor and interaction alignment results |
| First-person arms, damage, other weapons/scenes/outfits | Pending | Do not infer these from the supplied views |

The five screenshots are under `reports/runtime/2026-10-09/`: `first_gameplay_standing.png`,
`weapon_handling.png`, `ads_hair_hood_clipping.png`, `cutscene_closeup.png`, and
`v0.1.1_ads_hair_residual.png`.
Each observation includes the image SHA256 and distinguishes visual findings
from the user's motion/quality report.

The first [headwear correction](HEADWEAR.md) was installed by the user as complete
v0.1.1. It reduced the reported clipping but did not resolve it. The installed
identity was checked again in observation 05, ruling out stale v0.1.0 files as
the explanation. The earlier rear-only diagnostic mask and head/chest fixtures
missed some forward-card and shoulder deformation cases.

The second candidate extends hood-derived weights onto lower forward locks and
checks all hair cards in 14 synthetic poses, including arms/shoulders. It retains
geometry/materials/Grace rig and all non-hair weights. Complete v0.1.2 requires a
new user-run ADS and cutscene retest; offline improvements are not a runtime pass.
Then finish walking/turning, crouching, stairs and floor contact. Keep facial
retargeting separate so the cause of regressions remains clear.

