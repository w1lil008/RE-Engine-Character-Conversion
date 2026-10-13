# Third-party tools and data

This source snapshot does not vendor external tools, libraries, game data, or their binaries. Lock files document versions, upstream repositories, commits, and archive hashes for dependencies used during local development.

Before provisioning a tool, retrieve it from the cited upstream source and review its current license and terms. The lock files are provenance records, not a grant to redistribute those tools. The inspected RE-Engine-Lib source revision is MIT-licensed upstream; other tool licenses should be confirmed from the corresponding upstream checkout because their source and license files are not included here.

The pipeline uses game installations and locally extracted resources. Those resources remain the property of their respective rights holders and are deliberately excluded from this repository. Keep local game-derived files, tool checkouts, and generated outputs in ignored `assets/`, `tools/`, and `build/` directories. Do not commit them or include them in release archives.

No project license is currently provided. The absence of a license means this repository does not grant permission to reuse its original code or documentation. Third-party licenses continue to govern their respective works.
