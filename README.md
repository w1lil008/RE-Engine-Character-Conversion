# Bela RE8 → RE9 conversion research

This repository preserves the original engineering source and documentation behind a research project adapting Bela Dimitrescu from *Resident Evil Village* (RE8) for *Resident Evil Requiem* (RE9). The work covers native mesh and material conversion, retaining Grace Ashcroft’s 611-joint runtime skeleton, offline reconstruction and retargeting of Bela animation, native MOT/MOTLIST encoding experiments, and read-only REFramework diagnostics.

The project produced a playable character-replacement prototype and an offline-validated five-second idle retarget. The converted native animation has passed structural and sampled-transform checks, but its runtime loading, controller binding, and playback in RE9 remain unverified. The v0.1.3 prototype also still needs the project owner’s in-game confirmation. This repository is research source; it is not an installable mod or a self-contained build environment.

## What is included

- Original Python and Lua utilities, tests, configuration examples, release notes, and technical reports.
- A v0.2.0 animation-conversion roadmap and offline retargeting/native-format research.
- Pinned references and hashes for external tools, so a developer can provision compatible local dependencies.
- A small portable test subset for the source-animation math and retargeting utilities.

## What is excluded

No Capcom game archives or extracted assets are included: no meshes, textures, native game resources, animation payloads, Blender scenes, videos, screenshots, or installable mod packages. Game-derived assets and generated build products belong in local ignored directories only. The published history starts from a clean source-only snapshot; earlier development commits were excluded because they contained local paths and generated evidence.

Some configuration and research notes contain resource identifiers and filenames needed to explain the engineering work. They are metadata, not redistributed game payloads. Do not use them as a substitute for assets from a game installation you are authorized to access.

## Quick start: portable checks

Use Python 3.12. Install NumPy, then run the test subset that does not require extracted game assets or external RE Engine tools:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install numpy==2.3.5
python -m unittest discover -s tests -p test_source_animation.py -v
python -m unittest discover -s tests -p test_retarget_idle.py -v
```

These tests exercise portable math and validation paths; tests that need omitted asset payloads are skipped. Passing them does not validate game integration.

## Full local setup

The conversion pipeline requires authorized local RE8 and RE9 installations, extracted inputs generated locally, Blender 4.3.2, and external RE Engine tools at the versions and commits in [`config/toolchain.lock.json`](config/toolchain.lock.json). Animation-format research also references a separately retrieved RE-Engine-Lib revision in [`config/animation_research.lock.json`](config/animation_research.lock.json). External tools are not bundled. Follow their upstream installation instructions and licenses; do not commit tool checkouts, extracted data, generated outputs, or game files.

Set local paths in `config/project.json` and provision the pinned dependencies. The complete integration suite additionally expects extracted and generated files under ignored `assets/` and `build/` directories and, for Lua tests, the optional `lupa` package. C# bridge projects require the pinned RE-Engine-Lib checkout and a generated `UpstreamFrameSampler.cs` produced by the project workflow. See [`docs/PIPELINE.md`](docs/PIPELINE.md), [`docs/THIRD_PARTY.md`](docs/THIRD_PARTY.md), and the lock files before running pipeline scripts. The full suite is not expected to pass on a fresh clone until those local prerequisites have been supplied.

## Current limitations

- No game assets or packaged mod are available from this repository, so a fresh clone cannot rebuild or install the character replacement by itself.
- Native animation loading and runtime binding are not proven. The two full-XYZW quaternion tracks in particular remain a runtime compatibility question.
- The retarget keeps Grace’s playable skeleton and controls; some motion differences reflect her proportions and the accepted prototype retains rigid dress folds and neutral finger poses.
- Facial animation, blinking, lip-sync, cloth physics, and broader original-animation integration are outside the completed scope.
- Original project code and documentation are licensed under the [MIT License](LICENSE). That license does not cover Capcom game assets, third-party tools, or other material identified in the repository; their respective rights and terms still apply.

## Suggested repository identity

- Repository name: `bela-re8-to-re9-research`
- Description: Source-only tools and engineering notes for adapting Bela Dimitrescu’s RE8 character and animation to RE9; no game assets or mod packages included.

See [`ROADMAP_V0.2.0.md`](ROADMAP_V0.2.0.md) for planned animation integration and the distinction between verified findings and open questions.
