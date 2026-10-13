// Independent read-only JMAP28 verification using the pinned ReeLib reader.
using System.Security.Cryptography;
using System.Text.Json;
using ReeLib;
if (args.Length != 2) throw new ArgumentException("input.jmap.28 fresh-workspace-output.json");
if (File.Exists(args[1])) throw new IOException("Preserve existing evidence; choose a fresh output");
var bytes = File.ReadAllBytes(args[0]);
using var handler = new FileHandler(new MemoryStream(bytes, writable: false), args[0]);
var file = new JmapFile(handler);
if (!file.Read() || file.Header.Version != 28) throw new InvalidDataException("Expected valid JMAP28");
var output = new {
    sha256 = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant(),
    version = file.Header.Version, attribute_flags = file.Header.attributeFlags,
    joint_mask_groups = file.MaskGroups.Select(g => new {group_id = g.groupId,
        joints = g.Masks.Select(j => new {hash = j.jointHash, mask_byte = j.mask,
            weight = j.weight})}),
    ik_definitions = file.IkMotionData.Select(j => new {ik_joint_hash = j.ikJointNameHash,
        fk_joint_hash = j.fkJointNameHash, type = (int)j.ikType, descendant_level = j.descendantLevelFromIkHandle,
        direction = (int)j.ikDirection, up_vector = (int)j.ikUpvector}),
    joint_expression_count = file.JointExpressionGroups.Expressions.Count,
    extra_joint_count = file.ExtraJoints.Joints.Count
};
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[1]))!);
File.WriteAllText(args[1], JsonSerializer.Serialize(output));
Console.WriteLine("Read-only JMAP28 decode completed");

