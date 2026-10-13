# Verified ecosystem and local findings

10 October update: the [v0.2.0 roadmap](../ROADMAP_V0.2.0.md) now records actual
RE8 MOTLIST 486 / MOT 458 and RE9 MOTLIST 1047 / MOT 983 samples, bank references,
340 related clip records and the facial/cloth investigation. This is metadata
research; no animation keyframes were converted or runtime hook implemented.
The older ecosystem findings below remain historical evidence.

Checked 9 October 2026. Statements below distinguish upstream support claims, local binary checks and untested runtime behaviour.

| Tool | Evidence of RE9 support | Project use |
|---|---|---|
| RE Mesh Editor v0.66 | Explicit RE9 support added in v0.62; RE9 presets added in v0.65 | Pinned readers/writers, presets, DDS/TEX conversion; local RE9 mesh/MDF/TEX round trips |
| RE Asset Library v0.25 | Supports the Mesh Editor game set | Pinned PAK reader and resource extraction; tested against both local games |
| Ekey REE.PAK.Tool | RE9 Steam filename list present in pinned source | Filename lists only; its executable has not been tested |
| REFramework | Explicitly lists Requiem | Existing local installation detected; no DLL/config changes |
| Fluffy Mod Manager 3.084 | Local author's changelog says RE9 support added in v3.070 | Existing manager detected; no mod installed by this project |
| RE Chain Editor v14.0 | Changelog explicitly adds RE9 | Candidate for later physics; not downloaded or tested here |
| REE Content Editor | Explicitly lists Requiem and Village; documents mesh and animation editing | Candidate for prefab/animation work; not installed or tested here |

[RE Mesh Editor](https://github.com/NSACloud/RE-Mesh-Editor) requires Blender 4.3.2 or higher. Its README warns about a Blender 5.1 performance issue. It and the two NSACloud editor/library repositories used here are archived; they should not be treated as actively maintained. The project pins 4.3.2 instead of assuming compatibility with the user's newly installed Blender.

[RE Asset Library](https://github.com/NSACloud/RE-Asset-Library) supplies established selective extraction. Its [catalog collection](https://github.com/NSACloud/RE-Asset-Library-Collection) contains discovery metadata rather than the character assets themselves. [Ekey's repository](https://github.com/Ekey/REE.PAK.Tool) supplies public resource filenames. Assets used here came from the two installed games.

[REFramework](https://github.com/praydog/REFramework) provides runtime loading and object inspection. The installed commit is recorded in `config/toolchain.lock.json`; the game log identifies RE9. Existing loose-file, loose-texture and alternate-PAK-directory settings are enabled. Hook warnings in the existing log remain a runtime-test concern.

Fluffy's **locally supplied** `readme.txt` documents mod folder layout and `modinfo.ini`; `change-log.txt` verifies RE9 support and installed version. The manager lives under the user's Downloads folder. This is stronger local evidence than inferring support from earlier RE games.

[Glitch5970's Alyssa-for-Grace mod](https://www.nexusmods.com/residentevilrequiem/mods/85) is a real model replacement example. Its author documents separate hand replacements, loose-file loading, and revisions addressing neck, facial animation, first-person visibility, holsters and scene physics. These are author-reported results for another character, not local proof that this Bela build works. They support using Grace's asset slots and treating these systems as separate test obligations.

[RE Chain Editor](https://github.com/NSACloud/RE-Chain-Editor) supports chain/chain2 and CLSP editing; its v14.0 changelog explicitly names RE9 even though the older supported-games list is incomplete. [REE Content Editor](https://github.com/kagenocookie/REE-Content-Editor) documents PAK access, prefab editing, animation preview/import/export and MOT retargeting. A fresh RE9-specific file test would still be needed before adopting either tool into the build.

Older Noesis wrappers and REtool have not been selected: RE9 compatibility was not established for this project's versions. A supported earlier game is not sufficient evidence.

## Formats actually read here

| Resource | RE8 local assets | RE9 local assets/output | Consequence |
|---|---|---|---|
| Mesh suffix | `.mesh.2101050001` | `.mesh.250925211` | Export through the RE9 writer; renaming RE8 files is insufficient |
| Mesh internal header | `2020091500` | `250904410` in writer output | Suffix and internal version are different fields |
| Material | `.mdf2.19` | `.mdf2.51` | Rebuild with RE9 shader presets and bindings |
| Texture | `.tex.30` | `.tex.250813143` | RE9 GDeflate encoding; local payload round trips tested |
| Physics resources | `.chain.39` | `chain2`/CLSP resources extracted | Not directly interchangeable; no physics replacement exported |
| Skeleton | Bind hierarchy/matrices embedded in meshes; other skeleton assets can exist | Original Grace mesh bind definitions retained | No runtime FBXSKEL replacement performed |
| Other rig/runtime resources | Prefabs, animation banks and expression resources are distinct from mesh data | PFB, JCNS and JNTEXPRGRAPH resources discovered/extracted | Not parsed semantically or modified by this prototype |

Source streaming TEX companions are preferred when present. Main RE9 meshes required their streaming vertex-data companions to parse. New prototype meshes embed their data; old streaming buffers are not copied into staging. Mask conversion swaps G and A from the source ATOC binding into the target preset's channel layout. Shader previews, original eye effects, wrinkle arrays, blood/wetness and vertex-animation cloth require further work.

Local RE9 TEX extraction exposed two compression layers: an outer PAK entry can declare compression zero while its TEX payload is internally GDeflated. Its TOC decompressed size describes the logical header/mip tables plus decoded mip sizes. The extractor now recognizes only the verified RE9 TEX version in this case, decodes every mip and checks that logical size. It does not waive size checks for arbitrary mismatches. The native writer also expects tangent XYZ/handedness prepacked into signed bytes, unlike normalized normals. These adapter conventions have been checked against source and local binary round trips.

## Rigging evidence

The source body and shared GPU-clothing skeletons have matching named bone origins in the locally extracted rest pose. Grace's bind definitions agree across her head, shirt, lower body and both arms within `1e-5`; merging them produces 611 bones. These measurements do not prove the runtime accepts every exported bone index.

Examples of semantic aliases are `L_UpperArm → L_Arm_Upper`, `L_Forearm → L_Arm_Lower`, `L_Hand → L_Arm_Hand`, and `Head → Head_0`. Facial `FACIAL_*` influences currently collapse to the head; neutral facial likeness is retained, expressions are not. Runtime gameplay animations are retained rather than transplanting Bela's enemy animation controller.

The first direct bind-matrix fit was rejected after visual inspection. Corresponding joint directions now define geometry fitting rotations; this avoids treating the games' bone roll conventions as equivalent. All matrices and fit residuals are recorded in analysis/mapping reports. Matching a bone name is a mapping suggestion, not animation compatibility proof.

