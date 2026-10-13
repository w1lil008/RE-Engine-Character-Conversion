-- Metadata only. No object construction, resources, hooks, getters on live
-- game objects, banks, setters, controller state or animation playback.
assert(reframework:get_game_name()=='re9' and sdk.get_tdb_version()==83,'Runtime mismatch')
assert(reframework:get_commit_hash()=='d1461375aee4ec3f313170f8eaad12064eb542d9','SDK mismatch')
local result={schema='bela-bank-api-v1',game='re9',tdb=83,metadata_only=true,types={}}
for _,name in ipairs({'via.motion.DynamicMotionBank','via.motion.Motion','via.motion.MotionInfo',
    'via.motion.MotionListResourceHolder','via.motion.JointMapResourceHolder','via.GameObject','via.Scene',
    'via.motion.AnimationTransformData','via.motion.TreeLayer','via.motion.MotionFsm2'}) do
    local d=sdk.find_type_definition(name)
    local row={type=name,available=d~=nil,methods={}}
    result.types[#result.types+1]=row
    local depth=0
    while d and depth<12 do
        local declaring=d:get_full_name()
        for _,m in ipairs(d:get_methods()) do
            local p={};for _,t in ipairs(m:get_param_types())do p[#p+1]=t:get_full_name()end
            local returned=m:get_return_type()
            row.methods[#row.methods+1]={name=m:get_name(),declaring_type=declaring,parameters=p,parameter_names=m:get_param_names(),
                returns=returned and returned:get_full_name() or 'unavailable',static=m:is_static(),
                function_reference=tostring(m:get_function())}
        end
        d=d:get_parent_type();depth=depth+1
    end
end
local occupied={};for _,p in ipairs(fs.glob('^bela_runtime_test[\\\\/].*\\.json$'))do occupied[p:gsub('\\','/')]=true end
local serial=1;local path='bela_runtime_test/bank_api_'..os.date('!%Y%m%dT%H%M%SZ')..'_'..serial..'.json'
while occupied[path]do serial=serial+1;path='bela_runtime_test/bank_api_'..os.date('!%Y%m%dT%H%M%SZ')..'_'..serial..'.json'end
assert(json.dump_file(path,result,4));assert(fs.read(path)==json.dump_string(result,4))
log.info('Bela bank API metadata saved: '..path)
return result

