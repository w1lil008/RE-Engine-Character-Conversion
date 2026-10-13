-- Simulated API only; never evidence of engine support.
fixture_time=0;fixture_mutations=0;fixture_files={};fixture_drop_layers=false;fixture_missing_joint=false;fixture_interrupt=false
local function tdname(n)return {get_full_name=function()return n end}end
local serial=100
local function object(name,definitions)
 serial=serial+1;local o={address=serial};local methods={}
 for _,def in ipairs(definitions)do
  local n,p,r,fn=def[1],def[2],def[3],def[4]
  methods[#methods+1]={get_name=function()return n end,get_param_types=function()local out={};for _,v in ipairs(p)do out[#out+1]=tdname(v)end;return out end,
    get_return_type=function()return tdname(r)end,is_static=function()return false end,
    call=function(_,obj,...)if n:match('^set') or n=='setupMotionBank' or n=='changeMotion' or n=='clearMotionResource' then fixture_mutations=fixture_mutations+1 end;return fn(obj,...)end}
 end
 local td={get_full_name=function()return name end,get_methods=function()return methods end,get_parent_type=function()return nil end}
 o.get_type_definition=function()return td end;o.get_address=function()return o.address end;return o
end
local function layer()
 local o=object('via.motion.TreeLayer',{
  {'get_MotionBankID',{},'System.UInt32',function(o)return o.bank end},
  {'get_MotionID',{},'System.UInt32',function(o)return o.id end},
  {'get_Frame',{},'System.Single',function(o)return o.frame end},
  {'get_EndFrame',{},'System.Single',function(o)return o.ending end},
  {'get_Enabled',{},'System.Boolean',function(o)return o.enabled end},
  {'get_BlendRate',{},'System.Single',function(o)return o.weight end},
  {'get_JointMaskID',{},'System.UInt32',function(o)return o.mask end},
  {'get_JointCount',{},'System.Int32',function()return 80 end},
  {'get_Setuped',{},'System.Boolean',function()return true end},
  {'get_Loop',{},'System.Boolean',function()return true end},
  {'get_Speed',{},'System.Single',function()return 1.0 end},
  {'getMotionInfo',{'via.motion.MotionInfo'},'System.Boolean',function()return true end},
  {'get_BlendMode',{},'via.motion.BlendMode',function()return 0 end},
  {'set_BlendMode',{'via.motion.BlendMode'},'System.Void',function()end},
  {'set_BaseLayerNo',{'System.UInt32'},'System.Void',function()end},
  {'set_JointMaskID',{'System.UInt32'},'System.Void',function(o,x)o.mask=x end},
  {'set_Enabled',{'System.Boolean'},'System.Void',function(o,x)o.enabled=x end},
  {'set_BlendRate',{'System.Single'},'System.Void',function(o,x)assert(math.type(x)=='float');o.weight=x end},
  {'clearMotionResource',{},'System.Void',function(o)o.id=4294967295 end},
  {'changeMotion',{'System.UInt32','System.UInt32','System.Single'},'System.Void',function(o,b,m,f)assert(math.type(f)=='float');o.bank=b;o.id=m;o.frame=f;o.ending=300 end},
  {'getJointIndexByNameHash',{'System.UInt32'},'System.Int32',function()return fixture_missing_joint and -1 or 0 end},
  {'getLocalRotation',{'System.Int32'},'via.Quaternion',function()return {x=0,y=0,z=0,w=1}end},
  {'getLocalPosition',{'System.Int32'},'via.vec3',function()return {x=0,y=0,z=0}end}})
 o.bank=0;o.id=1;o.frame=0.0;o.ending=1.0;o.enabled=true;o.weight=1.0;o.mask=0;return o
end
local map=object('via.motion.JointMapResourceHolder',{{'get_ResourcePath',{},'System.String',function()return 'GameAssets/Character/CharacterPrefab/cp_A1/cp_A100/JointMap/cp_A1JointMap.jmap'end}})
local go=object('via.GameObject',{})
fixture_motion=object('via.motion.Motion',{
 {'get_GameObject',{},'via.GameObject',function()return go end},
 {'get_JointMap',{},'via.motion.JointMapResourceHolder',function()return map end},
 {'get_JointCount',{},'System.Int32',function()return 80 end},
 {'getLayerCount',{},'System.UInt32',function(o)return o.layer_count end},
 {'getLayer',{'System.UInt32'},'via.motion.TreeLayer',function(o,i)return o.layers[i]end},
 {'getDynamicMotionBankCount',{},'System.Int32',function(o)return o.bank_count end},
 {'getDynamicMotionBank',{'System.Int32'},'via.motion.DynamicMotionBank',function(o,i)return o.banks[i]end},
 {'getMotionInfo',{'System.UInt32','System.Int32','System.UInt32','via.motion.MotionInfo'},'System.Boolean',function(o,b)return b==65000 and o.banks[3]~=nil end},
 {'setDynamicMotionBankCount',{'System.Int32'},'System.Void',function(o,n)for i=n,o.bank_count-1 do o.banks[i]=nil end;o.bank_count=n end},
 {'setDynamicMotionBank',{'System.Int32','via.motion.DynamicMotionBank'},'System.Void',function(o,i,b)o.banks[i]=b end},
 {'setupMotionBank',{},'System.Void',function()end},
 {'setLayerCount',{'System.UInt32'},'System.Void',function(o,n)
   if fixture_drop_layers then o.layers={}else for i=n,o.layer_count-1 do o.layers[i]=nil end end;o.layer_count=n end},
 {'setLayer',{'System.UInt32','via.motion.TreeLayer'},'System.Void',function(o,i,l)o.layers[i]=l end}})
fixture_motion.layers={};fixture_motion.banks={};fixture_motion.layer_count=17;fixture_motion.bank_count=3
for i=0,16 do fixture_motion.layers[i]=layer()end
fixture_original=fixture_motion.layers[0]
sdk={get_tdb_version=function()return 83 end,create_instance_global=function(n)
 if n=='via.motion.TreeLayer' then return layer()end
 if n=='via.motion.MotionInfo' then return object(n,{
 {'get_MotionName',{},'System.String',function()return 'Bela_Approved_Idle_Offline_300f_60fps'end},
 {'get_MotionEndFrame',{},'System.Single',function()return 300.0 end}})end
 if n=='via.motion.DynamicMotionBank' then return object(n,{
 {'set_BankID',{'System.UInt32'},'System.Void',function()end},
 {'set_OverwriteBankID',{'System.Boolean'},'System.Void',function()end},
 {'set_MotionList',{'via.motion.MotionListResourceHolder'},'System.Void',function()end}})end
 error('Unknown fixture type')
end,create_resource=function(_,p)
 return {create_holder_global=function()return object('via.motion.MotionListResourceHolder',{{'get_ResourcePath',{},'System.String',function()return p end}})end}
end}
os.clock=function()return fixture_time end;os.time=function()return fixture_time end
dofile=function()return {prepare=function()return true end,watches={{motion=fixture_motion,selection={name='cp_A100',joint_count=80}}}}end
reframework={get_game_name=function()return 're9'end,get_commit_hash=function()return 'd1461375aee4ec3f313170f8eaad12064eb542d9'end}
re={on_frame=function(f)fixture_frame=f end,on_draw_ui=function()end};imgui={}
fs={glob=function()local r={};for p in pairs(fixture_files)do r[#r+1]=p end;return r end,read=function(p)return fixture_files[p]end}
json={dump_string=function(d,n)return fixture_encode(d,n)end,dump_file=function(p,d,n)fixture_files[p]=fixture_encode(d,n);return true end}
fixture_config={mode='dry_run',session='one_cycle_fixture',native_sha256='48505359a3dd5411dc98582649964cce07c10a7114229d0a60db96dd5467c477',
 resource_path='Animation/bela_prototype/v020/engine_decode_20261011_c/bela_idle.motlist',
 gates={engine_decode=true,all_24_constraints=true,isolated_layer_lifecycle=true},tracks={{name='root',hash=1}}}
function fixture_advance(t)
 fixture_time=fixture_time+t
 if fixture_motion.layers[17] and fixture_motion.layers[17].enabled then fixture_motion.layers[17].frame=fixture_motion.layers[17].frame+t*60 end
 if fixture_interrupt then fixture_original.id=2 end
 fixture_frame()
end

