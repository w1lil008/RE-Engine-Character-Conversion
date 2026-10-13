# Reusable pipeline boundaries

Current animation plan: [ROADMAP_V0.2.0.md](../ROADMAP_V0.2.0.md). The first
proposed experiment reconstructs the original five-second daughters idle;
conversion and runtime integration require separate authorization. v0.1.3
preserves the accepted native model and introduces no animation/controller
changes. The boundaries below continue to apply.

Implemented reusable pieces are joint-landmark fitting, explicit bone aliases, weight merging/normalization, body-surface garment transfer, lower-garment weight fields, topology-based weight diffusion, bounded garment clearance, path confinement, input/output provenance and validation gates. The garment utilities accept coordinate-axis/bone-family inputs and preserve original geometry fitting weights separately from runtime weights. These methods operate on geometry and semantic names rather than a specific game's animation controller; they do not supply cloth simulation.

The current format adapter uses RE mesh row-vector matrices, engine Y-up/metres, embedded bind tables, native MDF/TEX and Grace's resource paths. Other games must supply their own coordinate/unit adapter, rig profile, material bindings and export/package adapter. A filename extension match is not enough.

A future neutral representation should retain triangulated positions, normals/tangents, UV sets, material roles, original weights, explicit bind/inverse matrices, bone hierarchy, semantic mapping and provenance. GLB can provide inspectable interchange, but auxiliary skinning, shader and attachment data must remain in sidecars when a format cannot represent them faithfully. No Unreal, Unity or proprietary-engine exporter has been implemented.

Animation retargeting is a later module: source/target rest transforms, joint axis calibration, root motion, IK contacts, end-effectors, twist distribution and unsupported-action handling. Current scripts perform rest geometry fitting and skin-weight mapping; they do not convert animation clips. Facial retargeting requires an expression correspondence layer and validation with actual animation samples, rather than bulk bone renaming.

Preserve the target game's controller, weapon sockets and interaction rig for initial ports. Plan physics separately: chain constraints, cloth collision, hair cards/strands and vertex animation are not portable simply because the geometry is. Each engine needs its own runtime and cutscene tests.

