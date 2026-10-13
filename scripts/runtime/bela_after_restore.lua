-- Read-only post-cleanup capture. No setters, hooks, resource creation or playback.
return function(config)
    assert(config.session:match('^[a-z0-9_]+$') and #config.session<=64)
    assert(not BelaOneCycle or (BelaOneCycle.phase=='COMPLETE' and not BelaOneCycle.bound))
    assert(reframework:get_game_name()=='re9' and sdk.get_tdb_version()==83)
    assert(reframework:get_commit_hash()=='d1461375aee4ec3f313170f8eaad12064eb542d9')
    local P=dofile(config.probe_path)
    assert(P.clear() and P.prepare() and #P.watches==1,'Unique Grace controller required')
    assert(P.watches[1].selection.name=='cp_A100' and P.watches[1].selection.joint_count==80)
    P.identity=true -- confirmed by exact live rig/constraint proof and current observed scene
    P.context='Main Care Centre atrium; TPS; Requiem; after complete native-layer rollback'
    P.keyboard=true;P.interval=.05;P.max_samples=600;P.max_seconds=50
    local motion=P.watches[1].motion
    local methods={}
    local function get(name,returns)
        local method=methods[name]
        if not method then
            local definition=motion:get_type_definition();local depth=0
            while definition and depth<12 and not method do
                for _,candidate in ipairs(definition:get_methods())do
                    if candidate:get_name()==name and not candidate:is_static() and #candidate:get_param_types()==0 and
                        candidate:get_return_type():get_full_name()==returns then method=candidate;break end
                end
                definition=definition:get_parent_type();depth=depth+1
            end
            assert(method,'Exact read-only API unavailable: '..name);methods[name]=method
        end
        return method:call(motion)
    end
    local function vec(value,axes)
        local result={}
        for _,axis in ipairs(axes)do
            local x=value[axis];assert(type(x)=='number' and x==x and math.abs(x)<math.huge)
            result[#result+1]=x
        end
        return result
    end
    local T={schema='bela-after-restore-v1',session=config.session,read_only=true,rows={},errors={},started=false,
        phase='WAITING',start_delay_seconds=8,created_clock=os.clock(),created_wall=os.time()}
    BelaAfterRestore=T
    local function save()
        local path='bela_runtime_test/'..config.session..'_after_restore.json'
        for _,existing in ipairs(fs.glob('^bela_runtime_test[\\\\/].*\\.json$'))do
            assert(existing:gsub('\\','/')~=path,'Preserve existing diagnostic output')
        end
        T.binding_capture_path=P.saved_path
        assert(json.dump_file(path,T,4));assert(fs.read(path)==json.dump_string(T,4));T.saved_path=path
    end
    re.on_frame(function()
        if T.phase=='COMPLETE' or T.phase=='FAILED' then return end
        local ok,err=pcall(function()
            if not T.started then
                if os.time()-T.created_wall<8 then return end
                assert(P.start());T.started=true;T.phase='CAPTURING';T.last=-math.huge
            end
            if not P.running then T.phase='COMPLETE';save();return end
            local now=os.clock();if now-T.last<.1 then return end;T.last=now
            assert(#T.rows<600)
            local row={clock=now,wall_utc=os.date('!%Y-%m-%dT%H:%M:%SZ'),
                root_mode=get('get_RootMotion','via.motion.RootPlayMode'),
                root_translation=vec(get('get_RootMotionTranslation','via.vec3'),{'x','y','z'}),
                original_root_translation=vec(get('get_OriginalRootMotionTranslation','via.vec3'),{'x','y','z'}),
                root_rotation=vec(get('get_RootMotionRotation','via.Quaternion'),{'x','y','z','w'}),
                original_root_rotation=vec(get('get_OriginalRootMotionRotation','via.Quaternion'),{'x','y','z','w'})}
            T.rows[#T.rows+1]=row
        end)
        if not ok then
            T.errors[#T.errors+1]=tostring(err);T.phase='FAILED'
            if P.running then P.stop('after-restore diagnostic exception') end
            pcall(save)
        end
    end)
    return T
end

