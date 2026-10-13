# Third-party tools and local assets

Pinned tools retain their original license files under `tools/`. RE Mesh Editor and RE Asset Library provide GPL-3.0 sources; portable Blender includes its own licenses. Ekey's repository is used for public filename lists. Texture conversion uses the dependencies distributed with RE Mesh Editor. Python libraries retain their supplied licenses.

Exact repository commits, download SHA256 values and portable Blender version are in `config/toolchain.lock.json` and `tools/provenance.jsonl`. No downloaded tool is bundled into a mod package, and no package is currently produced.

Character data was selectively extracted from the supplied local installations. It is not covered by tool licenses or owned by this project. Extracted/native files stay local and ignored by Git. Future public distribution should keep source scripts separate from game-derived assets and use an appropriate permission-aware distribution method.

