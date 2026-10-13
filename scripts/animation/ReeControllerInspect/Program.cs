// Read only the controller node table using the independent pinned ReeLib reader.
// No RSZ schema required; no source resource reserialization.
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using ReeLib;
using ReeLib.Bhvt;
using ReeLib.Common;
if (args.Length != 2) throw new ArgumentException("controller-folder fresh-output.json");
if (File.Exists(args[1])) throw new IOException("Choose a fresh evidence output");
static object Field(object o, string n) => o.GetType().GetField(n, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)!.GetValue(o)!;
static uint[] Id(NodeID id) => new uint[] {id.ID, id.exID};
var records = new List<object>();
foreach (var path in Directory.GetFiles(args[0], "*.motfsm2.45", SearchOption.AllDirectories).Order()) {
    var bytes = File.ReadAllBytes(path);
    if (BitConverter.ToUInt32(bytes) != 45) throw new InvalidDataException("Expected version 45");
    using var handler = new FileHandler(new MemoryStream(bytes, writable: false), path);
    var offset = BitConverter.ToInt64(bytes, 16);
    var reader = handler.WithOffset(offset); reader.Seek(0);
    var header = new ReeLib.Bhvt.Header(GameName.re9);
    header.Read(reader); reader.Seek(header.nodeOffset);
    var count = reader.Read<int>(); var nodes = new List<object>();
    for (int i = 0; i < count; i++) {
        var node = new BHVTNode(GameName.re9); node.Read(reader);
        var end = reader.Tell(); node.ReadName(reader, header.stringOffset); reader.Seek(end);
        nodes.Add(new {id = Id(node.ID), name = node.Name, parent = Id(node.ParentID), attributes = (ushort)node.Attributes,
            states = node.States.States.Select(s => new {target = Id((NodeID)Field(s, "targetNodeID")), map_id = s.transitionMapID}),
            all_states = node.AllStates.AllStates.Select(s => new {target = Id((NodeID)Field(s, "targetNodeID")), map_id = s.transitionMapID})});
    }
    records.Add(new {file = Path.GetFileName(path), sha256 = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant(),
        node_count = count, node_table_end = offset + reader.Tell(), nodes});
}
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[1]))!);
File.WriteAllText(args[1], JsonSerializer.Serialize(new {controllers = records}));
Console.WriteLine("Independent node decode: " + records.Count + " controllers");

