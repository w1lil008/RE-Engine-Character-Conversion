// Read-only bridge to the pinned upstream decoder. Never writes native MOT files.
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using ReeLib;
using ReeLib.Mot;

if (args.Length != 3) throw new ArgumentException("source.motlist offset output.json");
var bytes = File.ReadAllBytes(args[0]);
if (BitConverter.ToUInt32(bytes, 0) != 486 || BitConverter.ToUInt32(bytes, 4) != MotlistFile.Magic)
    throw new InvalidDataException("Only RE8 MOTLIST 486 is allowed in this source experiment");
long offset = Convert.ToInt64(args[1], 16);
if (offset < 0 || offset + 128 > bytes.Length || BitConverter.ToUInt32(bytes, (int)offset) != 458)
    throw new InvalidDataException("Invalid embedded RE8 MOT 458 offset");
// A memory-only FileHandler avoids ReeLib's default read/write file opening.
using var handler = new FileHandler(new MemoryStream(bytes, writable: false), args[0]);
var mot = new MotFile(handler.WithOffset(offset)) { Embedded = true };
if (!mot.Read()) throw new InvalidDataException("Upstream MOT read returned false");
long bonePointer = BitConverter.ToInt64(bytes, (int)offset + 16);
uint motSize = BitConverter.ToUInt32(bytes, (int)offset + 12);
MotFile? mainRest = null;
long restSourceOffset = offset;
if (!(motSize == 0 || bonePointer > 0 && bonePointer < motSize)) {
    // Same inherited-rest rule as MotlistFile.DoRead; this exact source list
    // stores its shared table in slot zero at 0x1d0.
    restSourceOffset = 0x1d0;
    mainRest = new MotFile(handler.WithOffset(restSourceOffset)) { Embedded = true };
    if (!mainRest.Read()) throw new InvalidDataException("Shared rest source read failed");
    mainRest.ReadBones(null);
}
mot.ReadBones(mainRest);
float[] V(Vector3 v) => [v.X, v.Y, v.Z];
float[] Q(Quaternion q) => [q.X, q.Y, q.Z, q.W];
object? Channel(Track? t, bool rotation) {
    if (t == null) return null;
    var mode = rotation ? t.RotationCompressionType.ToString() : t.TranslationCompressionType.ToString();
    if (mode.Contains("Unknown")) throw new NotSupportedException(mode);
    var values = rotation ? t.rotations!.Select(Q).ToArray() : t.translations!.Select(V).ToArray();
    if (values.Length != t.keyCount || values.Length == 0 ||
        (t.frameIndexes != null && t.frameIndexes.Length != values.Length))
        throw new InvalidDataException("Missing decoded keys or unsupported implicit timing");
    if (t.frameIndexes == null && values.Length != 1)
        throw new InvalidDataException("Multiple keys without native frame indices");
    return new { flags = t.flags, compression_hex = $"0x{t.Compression:x}", compression_mode = mode,
        frame_index_type = t.FrameIndexType.ToString(), key_count = t.keyCount,
        frames = t.frameIndexes, values, constant = t.frameIndexes == null || values.Length == 1 };
}
foreach (var c in mot.BoneClips) {
    if (((int)c.ClipHeader.trackFlags & ~7) != 0) throw new NotSupportedException("Unknown bone channel flags");
    if (mot.GetBoneByHash(c.ClipHeader.boneHash) == null) throw new InvalidDataException("Unbound bone track");
}
var output = new {
    decoder = "ReeLib ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef",
    resource_sha256 = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant(), offset, rest_table_source_offset = restSourceOffset,
    name = mot.Name, mot_version = (int)mot.Header.version, fps = mot.Header.FrameRate,
    frame_count = mot.Header.frameCount, start_frame = mot.Header.startFrame, end_frame = mot.Header.endFrame,
    blending = mot.Header.blending, attributes = (int)mot.Header.attributes,
    rest_bone_count = mot.Bones.Count, bone_track_count = mot.BoneClips.Count,
    behavior_clip_count = mot.Clips.Count, end_clip_count = mot.EndClips.Count,
    behavior_clips = mot.Clips.Select(c => new { category = c.category, use_flags = c.useFlags,
        tracks = c.ClipEntry.Tracks.Select(t => new { name = t.Name, start = t.startFrame, end = t.endFrame,
            properties = t.Properties.Select(p => p.Info.FunctionName).ToArray() }).ToArray(),
        key_count = c.ClipEntry.NormalKeys.Count }).ToArray(),
    property_track_count = mot.MotPropertyTracks.Count, property_tree_present = mot.PropertyList != null,
    vertex_animation_present = mot.VertexAnimation != null, joint_map_reference = mot.Header.jointMapPath,
    bones = mot.Bones.Select(b => new { name = b.boneName, index = b.Index, hash = b.boneHash,
        parent = b.Parent?.boneName, translation = V(b.translation), quaternion_xyzw = Q(b.quaternion),
        attributes1 = b.attributes1, attributes2 = b.attributes2 }).ToArray(),
    tracks = mot.BoneClips.Select(c => new { bone = c.ClipHeader.boneName, index = c.ClipHeader.boneIndex,
        hash = c.ClipHeader.boneHash, flags = (int)c.ClipHeader.trackFlags, weight = c.ClipHeader.weight,
        translation = Channel(c.Translation, false), rotation = Channel(c.Rotation, true),
        scale = Channel(c.Scale, false) }).ToArray()
};
var path = Path.GetFullPath(args[2]);
if (File.Exists(path)) throw new IOException("Preserve existing decoded output; choose a fresh path");
Directory.CreateDirectory(Path.GetDirectoryName(path)!);
File.WriteAllText(path, JsonSerializer.Serialize(output, new JsonSerializerOptions { WriteIndented = false }));
// Headless reference: upstream editor's actual FindFrames method, with its
// documented absolute-local TRS replacement and System.Numerics Lerp math.
// This validates editor sampling, not undiscovered RE8 procedural physics/IK.
string referencePath = Path.ChangeExtension(path, ".reference.bin");
if (File.Exists(referencePath)) throw new IOException("Preserve existing reference");
using (var writer = new BinaryWriter(File.Create(referencePath))) {
    int frames = (int)mot.Header.frameCount * 2 + 1;
    writer.Write(new byte[] { 66, 71, 83, 49 }); // BGS1; little-endian row-vector matrices
    writer.Write(frames); writer.Write(mot.Bones.Count);
    var byName = mot.Bones.Select((b,i)=>(b.boneName,i)).ToDictionary(x=>x.boneName,x=>x.i);
    Vector3 VectorChannel(Track? t, float f, Vector3 fallback) {
        if (t == null) return fallback;
        var (a,b,w) = UpstreamFrameSampler.FindFrames(t,f);
        return a < 0 ? fallback : Vector3.Lerp(t.translations![a],t.translations[b],w);
    }
    Quaternion RotationChannel(Track? t, float f, Quaternion fallback) {
        if (t == null) return fallback;
        var (a,b,w) = UpstreamFrameSampler.FindFrames(t,f);
        return a < 0 ? fallback : Quaternion.Lerp(t.rotations![a],t.rotations[b],w);
    }
    for (int frame=0;frame<frames;frame++) {
        float f = frame * .5f;
        writer.Write(f);
        var global = new Matrix4x4[mot.Bones.Count];
        var ready = new bool[mot.Bones.Count];
        Matrix4x4 Evaluate(int i) {
            if (ready[i]) return global[i];
            var bone=mot.Bones[i]; var c=mot.BoneClips.FirstOrDefault(c=>c.ClipHeader.boneHash==bone.boneHash);
            var p=VectorChannel(c?.Translation,f,bone.translation);
            var q=RotationChannel(c?.Rotation,f,bone.quaternion);
            var s=VectorChannel(c?.Scale,f,Vector3.One);
            var local=Matrix4x4.CreateScale(s)*Matrix4x4.CreateFromQuaternion(q)*Matrix4x4.CreateTranslation(p);
            global[i]=bone.Parent==null ? local : local*Evaluate(byName[bone.Parent.boneName]);
            ready[i]=true; return global[i];
        }
        for (int i=0;i<mot.Bones.Count;i++) {
            var m=Evaluate(i);
            foreach (float v in new float[]{m.M11,m.M12,m.M13,m.M14,m.M21,m.M22,m.M23,m.M24,
                m.M31,m.M32,m.M33,m.M34,m.M41,m.M42,m.M43,m.M44}) writer.Write(v);
        }
    }
}
Console.WriteLine($"Decoded {mot.Name}: {mot.Bones.Count} rest bones, {mot.BoneClips.Count} bone tracks");

