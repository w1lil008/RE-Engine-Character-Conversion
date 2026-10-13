// Independent pinned ReeLib native reader and an explicitly tested upstream writer.
// All input files are opened from read-only memory, never using default disk handlers.
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using ReeLib;
using ReeLib.Mot;

if (args.Length != 3) throw new ArgumentException("decode-list|decode-mot|upstream-roundtrip input output");
var options = new JsonSerializerOptions { IncludeFields = true, ReferenceHandler = ReferenceHandler.IgnoreCycles, MaxDepth = 128,
    NumberHandling = JsonNumberHandling.AllowNamedFloatingPointLiterals };
float[] V(Vector3 v) => [v.X,v.Y,v.Z];
float[] Q(Quaternion q) => [q.X,q.Y,q.Z,q.W];
object? Channel(Track? t, bool rotation) {
    if (t == null) return null;
    var mode = rotation ? t.RotationCompressionType.ToString() : t.TranslationCompressionType.ToString();
    if (mode.Contains("Unknown")) throw new NotSupportedException(mode);
    var values = rotation ? t.rotations!.Select(Q).ToArray() : t.translations!.Select(V).ToArray();
    if (values.Length != t.keyCount || values.Length == 0 || (t.frameIndexes != null && t.frameIndexes.Length != values.Length))
        throw new InvalidDataException("Missing channel values");
    if (t.frameIndexes == null && values.Length != 1) throw new InvalidDataException("Unsupported implicit timing");
    return new { flags=t.flags, compression=t.Compression, mode, frame_index_type=t.FrameIndexType.ToString(),
        count=t.keyCount, frames=t.frameIndexes, values };
}
object Snapshot(MotFile m) {
    foreach(var c in m.BoneClips) if (((int)c.ClipHeader.trackFlags & ~7) != 0) throw new NotSupportedException("Unknown channel flags");
    return new { name=m.Name, version=(int)m.Header.version, frame_count=m.Header.frameCount,
        start=m.Header.startFrame,end=m.Header.endFrame,fps=m.Header.FrameRate,blending=m.Header.blending,
        attributes=(int)m.Header.attributes,attributes2=m.Header.uknAttributes2,bone_count_header=m.Header.boneCount,
        property_count_header=m.Header.animatedPropertyCount,jmap=m.Header.jointMapPath,
        bones=m.Bones.Select(b=>new {name=b.boneName,index=b.Index,hash=b.boneHash,parent=b.Parent?.boneName,
            translation=V(b.translation),rotation=Q(b.quaternion),attributes1=b.attributes1,attributes2=b.attributes2}).ToArray(),
        tracks=m.BoneClips.Select(c=>new {bone=c.ClipHeader.boneName,index=c.ClipHeader.boneIndex,hash=c.ClipHeader.boneHash,
            flags=(int)c.ClipHeader.trackFlags,weight=c.ClipHeader.weight,
            translation=Channel(c.Translation,false),rotation=Channel(c.Rotation,true),scale=Channel(c.Scale,false)}).ToArray(),
        clips=m.Clips, end_clips=m.EndClips, property_tracks=m.MotPropertyTracks, property_tree=m.PropertyList,
        vertex_animation=m.VertexAnimation };
}
var bytes=File.ReadAllBytes(args[1]);
using var handler=new FileHandler(new MemoryStream(bytes,writable:false),args[1]);
object output;
if(args[0]=="decode-mot" || args[0]=="upstream-mot-roundtrip") {
    if(BitConverter.ToUInt32(bytes,0)!=983)throw new InvalidDataException("Expected MOT 983");
    var m=new MotFile(handler);if(!m.Read())throw new InvalidDataException("Read failed");
    if(args[0]=="upstream-mot-roundtrip") {
        using var stream=new MemoryStream();
        m.FileHandler=new FileHandler(stream,"memory.mot.983");
        if(!m.Write())throw new InvalidDataException("Write failed");
        if(File.Exists(args[2]))throw new IOException("Choose fresh output");
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[2]))!);
        File.WriteAllBytes(args[2],stream.ToArray());
        Console.WriteLine($"Upstream encoded unchanged {m.Name}, {m.BoneClips.Count} tracks");return;
    }
    output=Snapshot(m);
} else {
    if(BitConverter.ToUInt32(bytes,0)!=1047)throw new InvalidDataException("Expected MOTLIST 1047");
    var list=new MotlistFile(handler);if(!list.Read())throw new InvalidDataException("Read failed");
    if(args[0]=="upstream-roundtrip") {
        using var stream=new MemoryStream();
        list.FileHandler=new FileHandler(stream,"memory.motlist.1047");
        if(!list.Write())throw new InvalidDataException("Write failed");
        if(File.Exists(args[2]))throw new IOException("Choose fresh output");
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[2]))!);
        File.WriteAllBytes(args[2],stream.ToArray());
        Console.WriteLine($"Upstream encoded {list.MotFiles.Count} resources, {list.Motions.Count} indices");return;
    }
    if(args[0]!="decode-list")throw new ArgumentException("Unknown command");
    output=new {version=(int)list.Header.version,name=list.Name,base_list=list.Header.BaseMotListPath,
        motpack=list.Header.motpackFilepath,unknown_value=list.Header.uknValue,unknown_short=list.Header.uknNum,
        indices=list.Motions.Select(i=>new {motion_id=i.motNumber,@switch=i.Switch,joint_mask=i.jointMaskId,tag=i.tagHash,
            type=i.type,flags=(byte)i.flags,physics_flags=i.physicsFlags,data=i.data,
            resource=i.MotFile==null?-1:list.MotFiles.IndexOf(i.MotFile),override_clips=i.OverrideClips}).ToArray(),
        motions=list.MotFiles.Select(m=>m is MotFile native?Snapshot(native):throw new NotSupportedException("Non-MOT resource: "+m.Name)).ToArray()};
}
if(File.Exists(args[2]))throw new IOException("Choose fresh output");
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[2]))!);
File.WriteAllText(args[2],JsonSerializer.Serialize(output,options));
Console.WriteLine($"Decoded {args[0]}: {bytes.Length} bytes; SHA256 {Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant()}");

