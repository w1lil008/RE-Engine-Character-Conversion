# Bela → Grace RE Engine modding research

This repository contains source scripts, configuration templates, tests, and engineering notes for a Resident Evil Engine character replacement and animation research project.

## Asset and privacy boundary

This clean repository contains **no game archives, extracted meshes, textures, native game resources, gameplay screenshots, Blender scenes, mod packages, tool binaries, or generated analysis reports**. Those materials are intentionally excluded from this snapshot and its Git history. Obtain and use game assets only from installations you are authorized to access; do not add extracted or copyrighted game assets to commits.

The repository has one clean initial commit. It does not include the previous development history because earlier commits contain machine-specific paths, generated evidence, and gameplay captures. The original working repository remains separate and unchanged.

## Local setup

Edit config/project.json to provide local RE8 and RE9 installation locations. The example paths are placeholders. The pipelines also need the pinned or compatible tools listed in config/toolchain.lock.json; tool binaries and extracted source assets are not included.

Some integration and regression tests expect locally generated files derived from a user's own game installations. Their absence from this repository is intentional. Results from a locally provisioned workspace should not be interpreted as tests against assets included here.

## Scope

The scripts support mesh/material conversion research, geometry and skin-weight validation, offline animation reconstruction and retargeting, native animation encoding experiments, and read-only runtime diagnostics. Native animation activation and any game installation steps remain separate, user-controlled operations.

No license has been selected for this project. Do not assume permission to reuse or redistribute its code, documentation, or any referenced third-party work until the project owner adds applicable licensing terms.

