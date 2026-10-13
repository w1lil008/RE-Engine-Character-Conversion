-- Simulated loader/lifetime boundary. This is never evidence of RE9 support.
fixture_files={};fixture_native_calls=0;fixture_time=0
fixture_missing_manager=false;fixture_missing_resource=false;fixture_bad_write=false
fixture_bank_queries={};fixture_control_query_fails=false
fixture_scratch_mutations={};fixture_scratch_attached=false
fixture_owner_throws=false;fixture_owned_objects={};fixture_missing_destroy=false;fixture_component_failure=false
fixture_sample_calls={};fixture_sample_failure=false
fixture_layer_serial=700;fixture_layers_reset=false
local function typename(name)return {get_full_name=function()return name end}end
local function method(name,parameters,returns,callback,is_static)
 return {get_name=function()return name end,get_param_types=function()
  local out={};for _,p in ipairs(parameters)do out[#out+1]=typename(p)end;return out end,
 get_return_type=function()return typename(returns)end,is_static=function()return is_static or false end,
 call=callback}
end
local function typedef(name,methods)
 return {get_full_name=function()return name end,get_methods=function()return methods end,
 get_fields=function()return {}end,get_parent_type=function()return nil end}
end
os.time=function()return fixture_time end
os.clock=function()return fixture_time end
os.date=function()return '2026-10-10T00:00:00Z' end
dofile=function(path)if path=='fixture' then return fixture_sample_plan end;return {} end
reframework={get_game_name=function()return 're9' end,
 get_commit_hash=function()return 'd1461375aee4ec3f313170f8eaad12064eb542d9' end}
re={on_frame=function(fn)fixture_frame=fn end,on_draw_ui=function(fn)fixture_ui=fn end}
json={dump_string=function(doc,indent)return fixture_encode(doc,indent) end,
 load_file=function()return fixture_sample_plan end,
 dump_file=function(path,doc,indent)
  fixture_files[path]=fixture_bad_write and 'partial' or fixture_encode(doc,indent);return true
 end}
fs={glob=function()local names={};for name in pairs(fixture_files)do names[#names+1]=name end;return names end,
 read=function(path)return fixture_files[path]or ''end}
imgui={tree_node=function()return false end}
sdk={get_tdb_version=function()return 83 end,
 get_native_singleton=function()if not fixture_missing_manager then return {}end end,
 create_resource=function(_,path)
  fixture_native_calls=fixture_native_calls+1
  if fixture_missing_resource then return nil end
  local d=typedef('via.motion.MotionListResourceHolder',{
   method('get_ResourcePath',{},'System.String',function(_,o)return o.path end)})
  local h={path=path,get_type_definition=function()return d end,get_address=function()return 100 end}
  return {get_address=function()return 200 end,create_holder_global=function()return h end}
 end}
sdk.create_instance_global=function(name)
 if name=='via.motion.TreeLayer' then
  fixture_layer_serial=fixture_layer_serial+1
  local layer={address=fixture_layer_serial,enabled=true,rate=1,bank=0,motion=0}
  local d=typedef(name,{
   method('set_Enabled',{'System.Boolean'},'System.Void',function(_,o,v)o.enabled=v end),
   method('get_Enabled',{},'System.Boolean',function(_,o)return o.enabled end),
   method('set_BlendRate',{'System.Single'},'System.Void',function(_,o,v)assert(math.type(v)=='float');o.rate=v end),
   method('get_BlendRate',{},'System.Single',function(_,o)return o.rate end),
   method('clearMotionResource',{},'System.Void',function(_,o)o.cleared=true end),
   method('changeMotion',{'System.UInt32','System.UInt32','System.Single'},'System.Void',function(_,o,b,m,f)
    assert(math.type(f)=='float');assert(not o.enabled and o.rate==0);o.bank=b;o.motion=m end),
   method('get_MotionBankID',{},'System.UInt32',function(_,o)return o.bank end),
   method('get_MotionID',{},'System.UInt32',function(_,o)return o.motion end)})
  layer.get_type_definition=function()return d end;layer.get_address=function()return layer.address end;return layer
 end
 if name=='via.motion.AnimationTransformData' then
  local data={};local d=typedef(name,{
   method('clear',{},'System.Void',function(_,o)o.sample=nil end),
   method('get_ValidPosition',{},'System.Boolean',function(_,o)return o.sample.translation end),
   method('get_ValidRotation',{},'System.Boolean',function(_,o)return o.sample.rotation end),
   method('get_ValidScale',{},'System.Boolean',function(_,o)return o.sample.scale end),
   method('get_Position',{},'via.vec3',function()return {x=0,y=0,z=0}end),
   method('get_Rotation',{},'via.Quaternion',function()return {x=0,y=0,z=0,w=1}end),
   method('get_Scale',{},'via.vec3',function()return {x=1,y=1,z=1}end)})
  data.get_type_definition=function()return d end;return data
 end
 if name=='via.motion.MotionInfo' then
  local info={get_address=function()return 600 end}
  local d=typedef(name,{
   method('get_MotionEndFrame',{},'System.Single',function()return 300 end),
   method('get_BankID',{},'System.UInt32',function()return 0 end),
   method('get_MotionID',{},'System.UInt32',function()return 0 end),
   method('get_MotionName',{},'System.String',function(_,o)return o.name or 'Bela_Approved_Idle_Offline_300f_60fps' end),
   method('getAnimationTransform',{'System.UInt32','System.Single','via.motion.AnimationTransformData'},'System.Boolean',
    function(_,o,hash,frame,data)
     assert(math.type(frame)=='float','System.Single must receive a Lua float')
     fixture_sample_calls[#fixture_sample_calls+1]={hash=hash,frame=frame};
     if fixture_sample_failure then return false end
     for _,arm in ipairs(fixture_sample_plan.arms)do for _,track in ipairs(arm.tracks)do
      if track.hash==hash then data.sample=track end
     end end;return data.sample~=nil
    end)})
  info.get_type_definition=function()return d end;return info
 end
 if name=='via.motion.Motion' then
  local own_go=fixture_current_owner
  local motion={count=0,banks={},layers={},layer_count=0,owner=own_go,get_address=function()return 400 end}
  local d=typedef(name,{
   method('get_GameObject',{},'via.GameObject',function(_,o)
    if fixture_owner_throws then error('Invoke threw an exception')end
    if fixture_scratch_attached then return {} end;return o.owner end),
   method('getDynamicMotionBankCount',{},'System.Int32',function(_,o)return o.count end),
   method('setDynamicMotionBankCount',{'System.Int32'},'System.Void',function(_,o,n)
    fixture_scratch_mutations[#fixture_scratch_mutations+1]={object=o,count=n};o.count=n;if n==0 then o.banks={} end end),
   method('setDynamicMotionBank',{'System.Int32','via.motion.DynamicMotionBank'},'System.Void',function(_,o,n,bank)
    fixture_scratch_mutations[#fixture_scratch_mutations+1]={object=o,index=n};o.banks[n]=bank end),
   method('getDynamicMotionBank',{'System.Int32'},'via.motion.DynamicMotionBank',function(_,o,n)return o.banks[n] end),
   method('setupMotionBank',{},'System.Void',function(_,o)for _,b in pairs(o.banks)do b.initialized=true end end),
   method('getLayerCount',{},'System.UInt32',function(_,o)return o.layer_count end),
   method('setLayerCount',{'System.UInt32'},'System.Void',function(_,o,n)
    if fixture_layers_reset then o.layers={}else for i=n,o.layer_count-1 do o.layers[i]=nil end end;o.layer_count=n end),
   method('getLayer',{'System.UInt32'},'via.motion.TreeLayer',function(_,o,i)return o.layers[i] end),
   method('setLayer',{'System.UInt32','via.motion.TreeLayer'},'System.Void',function(_,o,i,l)o.layers[i]=l end),
   method('getMotionInfo',{'System.UInt32','System.Int32','System.UInt32','via.motion.MotionInfo'},'System.Boolean',function(_,o,b,_,_,info)
    if b==65000 then info.name='ch0200_GeneralM_0000_Idle_caution' end;return true end)})
  motion.get_type_definition=function()return d end
  return motion
 end
 assert(name=='via.motion.DynamicMotionBank')
 local bank={get_address=function()return 300 end}
 local d=typedef(name,{
  method('set_BankID',{'System.UInt32'},'System.Void',function(_,o,v)o.id=v end),
  method('set_OverwriteBankID',{'System.Boolean'},'System.Void',function(_,o,v)o.overwrite=v end),
  method('set_MotionList',{'via.motion.MotionListResourceHolder'},'System.Void',function(_,o,holder)o.holder=holder end),
  method('get_MotionList',{},'via.motion.MotionListResourceHolder',function(_,o)return o.holder end),
  method('hasDynamicMotion',{'System.UInt32','System.UInt32','System.Int32'},'System.Boolean',function(_,o,a,b,c)
   assert(a==0 and b==0 and c==0);fixture_bank_queries[#fixture_bank_queries+1]=o
   return not fixture_control_query_fails end)})
 bank.get_type_definition=function()return d end
 return bank
end
local go_definition
local create=method('create',{'System.String'},'via.GameObject',function(_,_,name)
 local go={name=name,address=500+#fixture_owned_objects,destroyed=false}
 go.get_address=function()return go.address end;go.get_type_definition=function()return go_definition end
 fixture_owned_objects[#fixture_owned_objects+1]=go;return go
end,true)
local destroy=method('destroy',{'via.GameObject'},'System.Void',function(_,_,go)go.destroyed=true end,true)
local component=method('createComponent',{'System.Type'},'via.Component',function(_,go)
 if fixture_component_failure then error('Component creation failed')end
 fixture_current_owner=go
 local motion=sdk.create_instance_global('via.motion.Motion');return motion
end)
local goname=method('get_Name',{},'System.String',function(_,go)return go.name end)
go_definition=typedef('via.GameObject',{create,destroy,component,goname})
sdk.find_type_definition=function(name)
 if name=='via.GameObject' then
  if fixture_missing_destroy then return typedef(name,{create,component,goname})end
  return go_definition
 end
 if name=='via.motion.TreeLayer' then return sdk.create_instance_global(name):get_type_definition() end
 if name=='via.motion.Motion' then
  local d=sdk.create_instance_global(name):get_type_definition();d.get_runtime_type=function()return {}end;return d
 end
end
fixture_config={session='fixture_test_01',resource_path='Animation/bela_prototype/v020/fixture_test_01/bela_idle.motlist',
 control_resource_path='Animation/ch/ch02/ch0200/motlist/ch0200_generalm.motlist',
 mode='resource_only',resource_bridge_build_checked=true,auto_start=true,auto_cleanup=true}
function fixture_advance(seconds)fixture_time=fixture_time+seconds;fixture_frame()end
fixture_sample_plan={schema='bela-engine-sample-plan-v1',native_sha256='fixture_hash',arms={
 {label='CONTROL',end_frame=300,frames={0,.5,300},tracks={{name='root',hash=1,rotation=true,translation=true,scale=false}}},
 {label='BELA',end_frame=300,frames={0,.5,300},tracks={{name='root',hash=2,rotation=true,translation=false,scale=false}}}}}

