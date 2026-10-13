# v0.1.3 stabilization record

10 October 2026. This patch preserves all 80 accepted v0.1.2 native payloads.
Its changes are reproducibility, validation, recovery and documentation. It
does not claim a new blink fix, dress motion improvement or runtime test.

## Baseline and source recovery

Current staging hashes match every entry in the v0.1.2 manifest. `dist` was
empty at inspection. The accepted archive was recovered from the existing
Fluffy manager copy and verified against SHA256
`77693eef1878c4ae68a2e69b54521d0ca8f0f257be0713680e1539d50e253165`.
`build/checkpoints/accepted_0.1.2/` contains that ZIP, `source_evidence.zip`
and copies of authoritative clothing/hair sidecars and preparation scene.
`reports/stabilization/baseline_checkpoint.json` records 291 source/evidence
files and 815 local inputs. Git checkpoint `codex/accepted-v0.1.2` is commit
`4e747d986a5e0234b6a71be5dcfe7df0b772b827`. Game-derived data remains local.

## Rebuild and validation

Run with the pinned Python runtime, from the project root:

```powershell
$projectPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $projectPython scripts/rebuild_v01.py --output build/rebuild_verify_new
& $projectPython -m unittest discover -s tests -v
```

Use a fresh output directory. `rebuild_v01.py` regenerates the mesh/MDF/TEX
outputs from extracted originals and hashed prepared sidecars; it re-exports
the hood-follow hair weights into separate files, then validates the assembled
result. No prior native payload is used as the base rebuild input. The hair
export reads the freshly rebuilt base hair. The existing prepared sidecars
are authored build inputs, including accepted clearance; regenerating a
manual Blender change from pristine game geometry is a different operation.
This task's build is `build/rebuild_0.1.2/natives_release`.

All 80 native outputs are byte-identical to accepted v0.1.2; all 41 textures
repeat the DDS/TEX pixel-payload checks. Eight meshes, 31 MDF variants and
41 TEX files pass current structural validation with zero errors. Grace's
611-bone hierarchy and all local/world/inverse bind matrices are compared
against the merged original Grace definitions. UV/normal streams are finite,
tangents and skin weights pass existing binary checks, dependencies resolve.
No skeleton/runtime animation assets are replaced.

Fourteen regression tests pass, including accepted hair topology, UVs,
normals, matrices and the head/neck/clavicle weight influences. Fourteen
current-native body poses and fourteen headwear poses pass finite geometry
checks; 20 renders were reviewed. The 92 tested skin seam groups remain within
1.36 mm; all 1,450 dress seam groups remain coincident in the selected poses.
These tests do not establish runtime collision, transitions or floor IK.

Current evidence is under `reports/stabilization/` and
`reports/stabilization_headwear/`. Historical reports are retained unchanged.

## Facial finding and release decision

Grace has `L/R_UprLd_*` and `L/R_LwrLd_*` controls, with weights on face and
lashes. Bela has `FACIAL_*Eyelid*` bones and eyelid/lash source weights.
The current mapping collapses `FACIAL_*` to `Head_0`; `L_Eye` and `R_Eye`
survive through exact-name mapping. Thus working gaze does not imply blink
deformation. Both original face meshes have nonzero blendshape-header
pointers; current output has none. The pinned RE Mesh Editor reader sets
`IMPORT_BLEND_SHAPES=False` and calls the implementation broken.

The original Grace prefab resource tables reference
`Animation/ch/ch02/ch0200/facial/motbank/ch0200_10.motbank`. All nine facial
bank/list resources and face JMAP were extracted read-only from official PAKs.
`ch0200_10_face_eyepose.motlist.1047` has 11 single-frame entries including
`ch0200_Face_Eye_Neutral`, `ch0200_Face_Eye_Close` and squeeze-close.
Headers specify 60 fps and 229 bone tracks. These are pose metadata, not a
decoded blink timing curve. Procedural trigger, blend timing and cutscene
invocation remain unknown. See `facial_and_garment_findings.json` and
`re9_facial_headers.json` for precise paths and hashes.

Do not ship speculative bone aliases or a handcrafted morph. First decode
neutral/closed poses, reproduce original Grace closure, adapt only Bela lids
and lashes, and validate clearance from both rotating eyeballs. That work is
deferred to the facial stream of v0.2.x. No neutral-face change is included.

## Garment finding and release decision

The current dress is standard linear skeletal skinning, built from body
surface transfer, a lower-leg weight field, 40 diffusion steps and up to
25 mm radial clearance. Native cloth, GPU cloth, vertex animation and added
garment bones are not included. The source name `gpucloth` does not imply
simulation survived conversion. Waist/shoulder weights and thigh correction
are unchanged. Current native imports show the known rigid folds/lifting under
strong crouch and stride surrogates. Larger edge strain is recorded in the
lower skirt; seam continuity is a separate property and is not used as proof
of natural motion. No new weight variant has sufficient evidence to replace
the accepted correction.

RE9 has native `.gpuc.250925365` resources on other Grace garment variants
and `.chain2.15` hair/garment resources. RE8 has `.gpuc.62` and `.chain.39`.
[ReeLib's GPUC adapter](https://github.com/kagenocookie/RE-Engine-Lib/blob/ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef/REE-Lib/OtherFiles/GpucFile.cs)
distinguishes their versions and topology/deformation structures. It does not
prove Bela-to-Grace cloth bindings work. Native cloth is research-dependent:
preserve the stable skeletal dress until topology, registration and collision
conversion are verified. No runtime physics dependency is added.

## Packaging and runtime scope

After reviewed evidence exists, `scripts/finalize_v01.py` stages the patch from
the rebuilt natives, verifies producer-script hashes and reruns tests. Then:

```powershell
& $projectPython scripts/finalize_v01.py --release-config config/releases/0.1.3.json
& $projectPython scripts/package_mod.py --release-config config/releases/0.1.3.json
```

The package is standalone and contains only natives, small release documents,
manifest and existing runtime screenshot. Package creation is one-shot: an
existing ZIP is never overwritten. Native and archive manifests are under
`reports/releases/0.1.3/`. The exact reproducibility check compares generated
payloads, not filenames alone.

The user's current task confirms successful playable rendering/movement,
aiming, cutscenes, lighting/materials and weapon handling in tested scenes.
Historical observation 06 specifically accepts the v0.1.2 ADS correction.
Neither establishes all actions, poses or outfit routing. v0.1.3 itself awaits
installation and the checklist in `docs/releases/0.1.3/MANUAL_TEST_CHECKLIST.txt`.
Rollback instructions and accepted ZIP hash are in that release's README.
No tool in this task writes game archives, saves or mod-manager state.

