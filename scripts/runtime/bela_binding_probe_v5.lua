-- Milestone D Stage 1. Manual load only. No animation/resource/controller writes.
-- Reflection is checked before every class of engine call; missing APIs stay missing.
if BelaBindingProbeV5 then return BelaBindingProbeV5 end -- Loading twice must not duplicate callbacks.
local P = {version = "D1.capture.5", candidates = {}, watches = {}, catalog = {}, errors = {},
    samples = {}, markers = {}, running = false, stopped = false, serial = 0,
    context = "Enter room/save context and camera mode", label = "idle",
    identity = false, max_samples = 600, max_seconds = 120, interval = 0.2,
    max_layers = 16, max_nodes = 4, max_watches = 4, calls = 0, peak_ms = 0,
    keyboard = false, marker_step = 1, deps_ok = false, show_environment = false}
local cache, disabled = {}, {}
-- These names are collected as reflection evidence ONLY, never admitted to invoke().
local RESEARCH = {"setDynamicMotionBankCount", "setDynamicMotionBank", "set_MotionList", "set_BankID", "set_OverwriteBankID",
    "changeMotion", "getMotionInfoByIndex", "getJoint", "get_Joint", "getJointName", "get_JointMap",
    "getJointCount", "getLayerCount", "getDynamicMotionBankCount", "getMotionNodeCount"}
local MARKERS = {"idle", "walk", "idle_after_walk", "aim", "idle_after_aim", "reload", "interact", "camera_change"}
local ZERO = {"get_Name", "get_JointCount", "get_PlayState", "get_PlaySpeed",
    "get_Frame", "get_EndFrame", "get_Speed", "get_Weight", "get_BlendWeight",
    "get_MotionID", "get_MotionBankID", "get_BankID", "get_BankType",
    "get_BankTypeMask", "get_MotionName", "get_Switch", "get_SwitchValue",
    "get_JointMask", "get_JointMaskID", "get_WrapMode", "get_Enabled",
    "get_CurrentNodeID", "get_CurrentNodeName", "get_CurrentState", "get_State",
    "get_IsBlending", "get_InterpolationFrame", "get_RootMotion", "get_UseIK", "get_OverwriteBankID", "get_TargetBankType"}
local EXTRA = {"get_GameObject", "get_Components", "get_Layer", "get_ActiveMotionBank",
    "get_DynamicMotionBank", "get_MotionBank", "get_MotionList", "get_Resource",
    "get_Path", "ToString", "getLayerCount", "getLayer", "getMotionNodeCount",
    "getMotionNode", "getDynamicMotionBankCount", "getDynamicMotionBank",
    "findComponents", "get_CurrentScene", "get_Count", "get_Item", "get_MotionBankAsset", "get_MotionBankIDTbl", "get_MergedMotionBankIDTbl"}
local allowed = {}
for _, name in ipairs(ZERO) do allowed[name] = true end
for _, name in ipairs(EXTRA) do allowed[name] = true end

local function attempt(fn, ...)
    local ok, value = pcall(fn, ...)
    if ok then return value end
    return nil
end
local function diagnostic(message)
    if #P.errors < 100 then P.errors[#P.errors + 1] = {probe = tostring(message):sub(1, 256)}
    else P.errors_truncated = true end
end
function P.dependencies()
    local missing = {}
    for group, names in pairs({sdk = {"find_type_definition", "get_native_singleton", "get_tdb_version", "typeof", "call_native_func"},
        re = {"on_frame", "on_draw_ui"}, json = {"dump_file", "dump_string", "load_file"}, fs = {"glob", "read"}}) do
        for _, name in ipairs(names) do
            if not _G[group] or type(_G[group][name]) ~= "function" then missing[#missing + 1] = group .. "." .. name end
        end
    end
    if not reframework then missing[#missing + 1] = "reframework" end
    table.sort(missing); P.missing_dependencies = missing; P.deps_ok = #missing == 0
    if not P.deps_ok then P.status = "Missing SDK dependencies: " .. table.concat(missing, ", ") end
    return P.deps_ok
end
local function td(obj) return obj and attempt(function() return obj:get_type_definition() end) end
local function type_name(def) return def and attempt(function() return def:get_full_name() end) or "unavailable" end
local function descriptor(obj)
    if obj == nil then return {unavailable = true} end
    return {type = type_name(td(obj)), address = tostring(attempt(function() return obj:get_address() end) or "unavailable")}
end
local function scalar(v)
    local t = type(v)
    if t == "number" then if v == v and math.abs(v) < math.huge then return v end
    elseif t == "string" then return v:sub(1, 512)
    elseif t == "boolean" then return v end
    return nil
end
local function metadata(def)
    local name = type_name(def)
    if cache[name] then return cache[name] end
    local data = {methods = {}, fields = {}, name = name}
    cache[name] = data
    if not def then return data end
    local cursor, depth = def, 0
    while cursor and depth < 12 do
        for _, method in ipairs(attempt(function() return cursor:get_methods() end) or {}) do
            local n = attempt(function() return method:get_name() end)
            local params = {}
            for _, param in ipairs(attempt(function() return method:get_param_types() end) or {}) do
                params[#params + 1] = type_name(param)
            end
            local m = {name = n, parameters = params,
                count = attempt(function() return method:get_num_params() end),
                returns = type_name(attempt(function() return method:get_return_type() end)),
                static = attempt(function() return method:is_static() end)}
            if n then
                data.methods[n] = data.methods[n] or {}
                data.methods[n][#data.methods[n] + 1] = {method = method, info = m}
            end
        end
        for _, f in ipairs(attempt(function() return cursor:get_fields() end) or {}) do
            local n = attempt(function() return f:get_name() end)
            if n and not data.fields[n] then
                data.fields[n] = {name = n, type = type_name(attempt(function() return f:get_type() end)),
                    static = attempt(function() return f:is_static() end)}
            end
        end
        cursor = attempt(function() return cursor:get_parent_type() end)
        depth = depth + 1
    end
    local public = {type = name, methods = {}, fields = {}, missing_zero_getters = {}, integration_method_candidates = {}}
    for _, n in ipairs(RESEARCH) do
        for _, entry in ipairs(data.methods[n] or {}) do
            public.integration_method_candidates[#public.integration_method_candidates + 1] = entry.info
        end
    end
    for _, n in ipairs(ZERO) do if not data.methods[n] then public.missing_zero_getters[#public.missing_zero_getters + 1] = n end end
    local names = {}; for n in pairs(data.methods) do names[#names + 1] = n end; table.sort(names)
    for _, n in ipairs(names) do
        for _, entry in ipairs(data.methods[n]) do
            if #public.methods < 350 then public.methods[#public.methods + 1] = entry.info else public.methods_truncated = true end
        end
    end
    for _, f in pairs(data.fields) do if #public.fields < 200 then public.fields[#public.fields + 1] = f else public.fields_truncated = true end end
    table.sort(public.fields, function(a, b) return a.name < b.name end)
    if #P.catalog < 160 then P.catalog[#P.catalog + 1] = public end
    return data
end

-- Single engine invocation gateway. Non-whitelisted calls cannot reach the engine.
local function invoke(obj, name, ...)
    if not obj or not allowed[name] then return nil end
    local d = metadata(td(obj)); local args = table.pack(...)
    local key = d.name .. ":" .. name
    if disabled[key] or P.calls >= 2500 then return nil end
    for _, candidate in ipairs(d.methods[name] or {}) do
        local m = candidate.info
        local types_ok = true
        if args.n == 1 then
            local expected = type(args[1]) == "number" and {['System.Int32'] = true, ['System.UInt32'] = true} or {['System.Type'] = true}
            types_ok = expected[m.parameters[1]] == true
        end
        if m.count == args.n and m.static == false and types_ok and #m.parameters == args.n then
            P.calls = P.calls + 1
            local ok, value = pcall(function() return candidate.method:call(obj, table.unpack(args, 1, args.n)) end)
            if ok then return value end
            disabled[key] = true
            if #P.errors < 100 then P.errors[#P.errors + 1] = {api = key, error = tostring(value):sub(1, 256)} end
            return nil
        end
    end
    return nil
end
local function elements(array, cap)
    if not array then return {} end
    -- SDK SystemArray getters, not game methods. No array writes.
    local count = attempt(function() return array:get_size() end)
    local result = {}
    if type(count) ~= "number" or count < 0 or count % 1 ~= 0 or count == math.huge then return result end
    for i = 0, math.min(count, cap) - 1 do
        local value = attempt(function() return array:get_element(i) end)
            or attempt(function() return array[i] end) -- SDK native arrays use zero-based indexing.
        if value then result[#result + 1] = value end
    end
    if count > cap then P.truncation = true end
    return result
end
local function array_entries(array, cap)
    local out = {}; local count = array and attempt(function() return array:get_size() end)
    if type(count) ~= "number" then count = invoke(array, "get_Count") end
    if type(count) ~= "number" or count < 0 or count % 1 ~= 0 or count == math.huge then return out end
    for i = 0, math.min(count, cap) - 1 do
        local value = attempt(function() return array:get_element(i) end) or attempt(function() return array[i] end) or invoke(array, "get_Item", i)
        out[#out + 1] = {index = i, object = value}
    end
    if count > cap then P.truncation = true end
    return out
end
local function properties(obj)
    local out = {object = descriptor(obj), observed = {}}
    if not obj then return out end
    for _, n in ipairs(ZERO) do
        local raw = invoke(obj, n); local v = scalar(raw)
        if v ~= nil then out.observed[n] = v
        elseif raw ~= nil then out.observed[n] = {reference = descriptor(raw), contents_not_decoded = true} end
    end
    local d = metadata(td(obj))
    for n, f in pairs(d.fields) do
        local relevant = false
        for _, hint in ipairs({"motion", "state", "mask", "ik", "blend", "frame", "bank", "switch", "weight", "weapon", "attach"}) do
            if n:lower():find(hint) then relevant = true end
        end
        if f.static == false and relevant then
            if P.calls < 2500 then
                P.calls = P.calls + 1
                local v = scalar(attempt(function() return obj:get_field(n) end))
                if v ~= nil then out.observed["field:" .. n] = v end
            end
        end
    end
    return out
end
local function resource(obj)
    local out = properties(obj)
    local path = scalar(invoke(obj, "get_Path")) or scalar(invoke(obj, "ToString"))
    if path then out.resource_string = path end
    return out
end
local function indexed(obj, getter, count_getter, cap)
    local out, count = {}, invoke(obj, count_getter)
    -- A count getter is required. No speculative out-of-range calls.
    if type(count) ~= "number" or count < 0 or count % 1 ~= 0 then return out end
    for i = 0, math.min(count, cap) - 1 do
        local item = invoke(obj, getter, i)
        out[#out + 1] = {index = i, object = item}
    end
    if count > cap then P.truncation = true end
    return out
end
local function layers(obj)
    local result = indexed(obj, "getLayer", "getLayerCount", P.max_layers)
    if #result == 0 then
        result = array_entries(invoke(obj, "get_Layer"), P.max_layers)
    end
    return result
end
local function banks(motion)
    local result = {}
    for _, getter in ipairs({"get_ActiveMotionBank", "get_DynamicMotionBank", "get_MotionBank"}) do
        for _, entry in ipairs(array_entries(invoke(motion, getter), 64)) do
            local bank = entry.object
            local row = properties(bank); row.source_getter = getter; row.index = entry.index
            row.motion_list = resource(invoke(bank, "get_MotionList"))
            row.resource = resource(invoke(bank, "get_Resource"))
            result[#result + 1] = row
        end
    end
    for _, entry in ipairs(indexed(motion, "getDynamicMotionBank", "getDynamicMotionBankCount", 64)) do
        local row = properties(entry.object); row.source_getter = "getDynamicMotionBank"; row.index = entry.index
        row.motion_list = resource(invoke(entry.object, "get_MotionList")); result[#result + 1] = row
    end
    return result
end
local function snapshot(watch)
    local row = {selection = watch.selection, role = watch.role, motion = properties(watch.motion),
        banks = banks(watch.motion), layers = {}, components = {},
        motion_bank_asset = resource(invoke(watch.motion, "get_MotionBankAsset")),
        motion_bank_ids = {}, merged_motion_bank_ids = {}}
    for _, pair in ipairs({{"get_MotionBankIDTbl", "motion_bank_ids"}, {"get_MergedMotionBankIDTbl", "merged_motion_bank_ids"}}) do
        for _, entry in ipairs(array_entries(invoke(watch.motion, pair[1]), 256)) do
            row[pair[2]][#row[pair[2]] + 1] = {index = entry.index, value = scalar(entry.object)}
        end
    end
    for _, entry in ipairs(layers(watch.motion)) do
        local layer = entry.object; local r = properties(layer); r.index = entry.index; r.nodes = {}
        local count = invoke(layer, "getMotionNodeCount")
        -- No guessed indices when RE9 exposes no count. The catalog records that gap.
        local valid_count = type(count) == "number" and count >= 0 and count % 1 == 0 and count < math.huge
        local upper = valid_count and math.min(count, P.max_nodes) or 0
        r.node_count = valid_count and count or nil; r.node_count_unavailable = not valid_count
        if valid_count and count > P.max_nodes then P.truncation = true end
        for i = 0, upper - 1 do
            local node = invoke(layer, "getMotionNode", i)
            local n = properties(node); n.index = i; r.nodes[#r.nodes + 1] = n
        end
        r.resource = resource(invoke(layer, "get_Resource")); row.layers[#row.layers + 1] = r
    end
    for _, comp in ipairs(watch.components) do
        local name = type_name(td(comp)):lower()
        if name:find("motion") or name:find("ik") or name:find("weapon") or name:find("attach") then
            local c = properties(comp); c.layers = {}
            if name:find("fsm") then
                for _, entry in ipairs(layers(comp)) do
                    local l = properties(entry.object); l.index = entry.index; c.layers[#c.layers + 1] = l
                end
            end
            row.components[#row.components + 1] = c
        end
    end
    return row
end
function P.discover()
    if P.running or not P.dependencies() then return end
    if #P.samples > 0 and not P.saved_path then P.status = "Save the retained capture before rediscovery"; return end
    P.calls = 0; P.candidates = {}; P.watches = {}; P.identity = false
    P.discovery_ok = false; P.discovery = {}
    cache = {}; disabled = {}; P.catalog = {}; P.errors = {}; P.errors_truncated = false; P.truncation = false
    P.runtime_identity = {game = attempt(function() return reframework:get_game_name() end),
        reframework_commit = attempt(function() return reframework:get_commit_hash() end),
        tdb_version = attempt(sdk.get_tdb_version)}
    P.discovery.runtime_identity = P.runtime_identity
    if P.runtime_identity.game ~= "re9" or P.runtime_identity.tdb_version ~= 83
        or P.runtime_identity.reframework_commit ~= "d1461375aee4ec3f313170f8eaad12064eb542d9" then
        P.status = "Game/framework/TDB identity mismatch or unavailable; no scene discovery performed"
        return
    end
    local def = sdk.find_type_definition("via.SceneManager")
    local mgr = sdk.get_native_singleton("via.SceneManager")
    P.discovery.scene_manager_type_available = def ~= nil
    P.discovery.scene_manager_singleton_available = mgr ~= nil
    if def then metadata(def) end
    local scene
    local method = def and attempt(function() return def:get_method("get_CurrentScene") end)
    P.discovery.current_scene_method_available = method ~= nil
    if method then
        P.discovery.current_scene_method = {count = attempt(function() return method:get_num_params() end),
            static = attempt(function() return method:is_static() end),
            returns = type_name(attempt(function() return method:get_return_type() end))}
    end
    -- Live D3 capture proves this particular RE9 getter is static (zero args,
    -- via.Scene return). The SDK invocation handles static dispatch itself.
    if mgr and method and attempt(function() return method:get_num_params() end) == 0
        and type_name(attempt(function() return method:get_return_type() end)) == "via.Scene" then
        local ok, value = pcall(sdk.call_native_func, mgr, def, "get_CurrentScene")
        if ok then scene = value else diagnostic("get_CurrentScene: " .. tostring(value)) end
    end
    local motion_type = sdk.find_type_definition("via.motion.Motion")
    P.discovery.scene_returned = scene ~= nil; P.discovery.scene_object = descriptor(scene)
    P.discovery.motion_type_available = motion_type ~= nil
    -- Type discovery alone is read-only; registration/playback functions are never called.
    P.integration_types = {}
    for _, name in ipairs({"via.motion.DynamicMotionBank", "via.motion.MotionLayer", "via.motion.MotionInfo", "via.motion.MotionListResource", "via.motion.MotionListResourceHolder"}) do
        local d = attempt(sdk.find_type_definition, name)
        P.integration_types[#P.integration_types + 1] = {type = name, reflected = d ~= nil}
        if d then metadata(d) end
    end
    local array = scene and motion_type and invoke(scene, "findComponents", sdk.typeof("via.motion.Motion"))
    P.discovery.component_array_returned = array ~= nil
    P.discovery.component_array_size = array and attempt(function() return array:get_size() end) or nil
    -- The observed atrium has 417 motion components. Keep discovery bounded,
    -- but do not cut the player off at the old 256-component limit.
    for _, motion in ipairs(elements(array, 2048)) do
        local go = invoke(motion, "get_GameObject")
        local name = scalar(invoke(go, "get_Name")) or "unnamed"
        P.candidates[#P.candidates + 1] = {motion = motion, go = go, name = name,
            joint_count = scalar(invoke(motion, "get_JointCount")), identity = descriptor(motion)}
    end
    P.discovery.candidate_count = #P.candidates
    P.discovery.getter_calls = P.calls
    P.discovery.calls_limit_reached = P.calls >= 2500
    if P.calls >= 2500 then P.truncation = true end
    if not scene then P.status = "Scene discovery failed; click Save discovery diagnostics"
    elseif not array then P.status = "findComponents returned no array; click Save discovery diagnostics"
    else P.discovery_ok = true; P.status = tostring(#P.candidates) .. " motion components discovered; confirm Grace selection" end
end
local function string_paths(value, out)
    if type(value) == "table" then
        for k, v in pairs(value) do
            if k == "resource_string" and type(v) == "string" then out[#out + 1] = v:lower()
            elseif type(v) == "table" then string_paths(v, out) end
        end
    end
end
function P.prepare()
    if P.running or (#P.samples > 0 and not P.saved_path) then return false end
    P.discover(); if not P.deps_ok or not P.discovery_ok then return false end
    local body, fps = {}, {}; P.calls = 0
    for i, c in ipairs(P.candidates) do
        local paths = {}; local lower_name = c.name:lower()
        local named_player = lower_name:find("cp_a100") or lower_name:find("grace") or lower_name:find("bela") or lower_name:find("ch0200")
        if c.joint_count == 611 or named_player then
            string_paths(banks(c.motion), paths)
            string_paths(resource(invoke(c.motion, "get_MotionBankAsset")), paths)
        end
        local has_body, has_fps = false, false
        for _, path in ipairs(paths) do
            if path:find("ch0200") and (path:find("motlist") or path:find("motbank")) then
                if path:find("fps") then has_fps = true
                elseif not path:find("face") and not path:find("facial") then has_body = true end
            end
        end
        c.selection_evidence = {joints = c.joint_count, resource_paths = paths, body_candidate = (has_body or named_player ~= nil) and c.joint_count == 611,
            fps_candidate = has_fps, heuristic_only = true}
        if c.selection_evidence.body_candidate then body[#body + 1] = i
        elseif has_fps then fps[#fps + 1] = i end
    end
    if #body == 1 then
        P.watch(body[1], "body")
        if #fps == 1 then P.watch(fps[1], "fps_arms") end
        P.status = "Unique 611-joint player candidate selected; verify Grace checkbox before capture"
        return true
    end
    P.status = "Grace selection ambiguous or unavailable; choose body manually. Candidates " .. #body
    return false
end
function P.watch(index, role)
    if P.running or #P.watches >= P.max_watches then return false end
    local c = P.candidates[index]; if not c then return false end
    for _, w in ipairs(P.watches) do if w.motion == c.motion then return false end end
    P.watches[#P.watches + 1] = {motion = c.motion, selection = {name = c.name,
        joint_count = c.joint_count, object = c.identity}, role = role or "unconfirmed",
        components = elements(invoke(c.go, "get_Components"), 48)}
    return true
end
function P.mark(label)
    if not P.running then return false end
    if #P.markers >= 256 then P.truncation = true; return false end
    P.label = label or P.label
    P.markers[#P.markers + 1] = {sample_index = #P.samples, label = P.label,
        elapsed_clock = P.running and os.clock() - P.start_clock or 0, wall_utc = os.date("!%Y-%m-%dT%H:%M:%SZ")}
end
function P.start()
    if #P.samples > 0 and not P.saved_path then P.status = "Save the retained capture before starting another"; return false end
    if P.running or #P.watches == 0 or not P.identity or not P.dependencies() then
        P.status = "Select Grace, confirm identity checkbox, and check dependencies before starting"; return false end
    P.samples = {}; P.markers = {}; P.serial = P.serial + 1; P.truncation = false
    P.start_clock = os.clock(); P.start_wall = os.time(); P.last_clock = -math.huge
    P.running = true; P.stopped = false; P.slow = 0; P.peak_ms = 0; P.marker_step = 1
    P.saved_path = nil; P.stop_reason = nil
    P.mark("idle"); return true
end
function P.document()
    local candidates = {}
    for _, c in ipairs(P.candidates) do candidates[#candidates + 1] = {name = c.name, joint_count = c.joint_count,
        identity = c.identity, selection_evidence = c.selection_evidence} end
    return {schema = "bela-runtime-binding-v2", probe_version = P.version, runtime_identity = P.runtime_identity,
        expected_build = "23634047", expected_reframework_commit = "d1461375aee4ec3f313170f8eaad12064eb542d9",
        build_identifiers_are_expectations_not_runtime_measurements = true,
        read_only = true, context = P.context, grace_identity_user_confirmed = P.identity,
        samples = P.samples, markers = P.markers, api_catalog = P.catalog, api_errors = P.errors,
        integration_types = P.integration_types,
        discovery = P.discovery,
        candidates = candidates,
        truncation = P.truncation, errors_truncated = P.errors_truncated,
        missing_dependencies = P.missing_dependencies, stop_reason = P.stop_reason, peak_sample_ms = P.peak_ms,
        limits = {sample_interval_clock_seconds = P.interval, maximum_samples = P.max_samples,
            maximum_wall_seconds = P.max_seconds, maximum_layers = P.max_layers, maximum_nodes = P.max_nodes},
        time_scope = "os.clock host clock; engine playback comes only from exposed Frame getters",
        state_change_scope = "Successive sampled getters; not a hooked complete controller transition trace"}
end
function P.stop(reason)
    P.running = false; P.stopped = true; P.stop_reason = reason or "manual"
    if P.saved_path then return true end -- Stop twice does not dump twice.
    if not P.dependencies() then return false end
    local ok, names = pcall(fs.glob, "^bela_d2[\\\\/].*\\.json$")
    if not ok or type(names) ~= "table" or #names > 10000 then
        P.status = "SAVE FAILED: cannot check filename conflicts; capture retained for retry"; return false
    end
    local occupied = {}; for _, name in ipairs(names) do occupied[name:gsub("\\", "/")] = true end
    local path = "bela_d2/" .. os.date("!%Y%m%dT%H%M%SZ") .. "_" .. P.serial .. ".json"
    local attempts = 0
    while occupied[path] and attempts < 10000 do
        attempts = attempts + 1; P.serial = P.serial + 1
        path = "bela_d2/" .. os.date("!%Y%m%dT%H%M%SZ") .. "_" .. P.serial .. ".json"
    end
    if occupied[path] then P.status = "SAVE FAILED: filename collision limit"; return false end
    local document = P.document(); local encoded = attempt(json.dump_string, document, 4)
    if not encoded or encoded == "" then P.status = "SAVE FAILED: JSON serialization; capture retained"; return false end
    local success, value = pcall(json.dump_file, path, document, 4)
    local text = attempt(fs.read, path); local decoded = attempt(json.load_file, path)
    if not success or not value or text ~= encoded or type(decoded) ~= "table" or decoded.schema ~= document.schema then
        P.status = "SAVE FAILED: write/read verification; capture retained for retry"; return false
    end
    P.saved_path = path
    P.status = "Stopped: " .. P.stop_reason .. "; " .. P.saved_path
    return true
end
function P.clear()
    if P.running or (#P.samples > 0 and not P.saved_path) then P.status = "Stop and save before clearing"; return false end
    P.watches = {}; P.candidates = {}; P.samples = {}; P.markers = {}; P.catalog = {}; P.errors = {}
    cache = {}; disabled = {}; P.identity = false; P.status = "Capture saved; Lua object references cleared"; return true
end
local keys = {}
function P.keyboard_tick()
    if not P.keyboard then return end
    for _, key in ipairs({0x75, 0x76, 0x77}) do -- Optional F6 start, F7 next action, F8 save.
        local down = attempt(function() return reframework:is_key_down(key) end) == true
        if down and not keys[key] then
            if key == 0x75 then P.start()
            elseif key == 0x76 and P.running then
                P.marker_step = math.min(P.marker_step + 1, 5); P.mark(MARKERS[P.marker_step])
            elseif key == 0x77 then P.stop("F8") end
        end
        keys[key] = down
    end
end
function P.tick()
    if not P.running then return end
    if #P.samples >= P.max_samples or os.time() - P.start_wall >= P.max_seconds then P.stop("capture limit"); return end
    local now = os.clock(); if now - P.last_clock < P.interval then return end
    P.last_clock = now; P.calls = 0
    local sample = {elapsed_clock = now - P.start_clock, marker = P.label, watches = {}}
    for _, watch in ipairs(P.watches) do sample.watches[#sample.watches + 1] = snapshot(watch) end
    sample.getter_calls = P.calls; sample.sample_ms = (os.clock() - now) * 1000
    P.peak_ms = math.max(P.peak_ms, sample.sample_ms)
    if P.calls >= 2500 then P.truncation = true end
    P.samples[#P.samples + 1] = sample
    P.slow = sample.sample_ms > 20 and P.slow + 1 or 0
    if P.slow >= 3 then P.stop("three samples exceeded 20 ms"); return end
end
function P.frame()
    local ok, err = pcall(function() P.keyboard_tick(); P.tick() end)
    if not ok then diagnostic(err); if P.running then P.stop("probe exception") end end
end
local function draw()
    if not imgui.tree_node("Bela D5 — read-only binding capture") then return end
    local ok, err = pcall(function()
    imgui.text("Read-only capture. No animation activation. Live RE9 API availability untested.")
    local changed; changed, P.context = imgui.input_text("Scene / camera / weapon", P.context)
    changed, P.identity = imgui.checkbox("I verified selected objects belong to Grace", P.identity)
    changed, P.keyboard = imgui.checkbox("Optional F6 start / F7 next action / F8 save", P.keyboard)
    if not P.running and imgui.button("Find Grace candidate") then P.prepare() end
    if not P.running and imgui.button("Discover / reset selection") then P.discover() end
    if not P.running and imgui.button("Save discovery diagnostics") then P.stop("discovery diagnostics") end
    if not P.running then
        changed, P.show_environment = imgui.checkbox("Show environmental objects", P.show_environment)
        for i, c in ipairs(P.candidates) do
            local name = c.name:lower()
            local relevant = c.joint_count == 611 or name:find("cp_") or name:find("ch0200") or name:find("grace") or name:find("bela") or name:find("player")
            if P.show_environment or relevant then
            if imgui.tree_node(i .. ": " .. c.name .. " (joints " .. tostring(c.joint_count) .. ")") then
                imgui.text(c.identity.type .. " @ " .. c.identity.address)
                if imgui.button("Watch as body##" .. i) then P.watch(i, "body") end
                if imgui.button("Watch as FPS arms##" .. i) then P.watch(i, "fps_arms") end
                if imgui.button("Watch as other##" .. i) then P.watch(i, "other") end
                imgui.tree_pop()
            end
            end
        end
        imgui.text("Selected " .. #P.watches .. "/4")
        if imgui.button("Start capture") then P.start() end
        if #P.samples > 0 and not P.saved_path and imgui.button("Retry save") then P.stop("save retry") end
        if imgui.button("Clear saved capture / release Lua references") then P.clear() end
    else
        for _, label in ipairs(MARKERS) do if imgui.button("Mark " .. label) then P.mark(label) end end
        if imgui.button("Stop and save") then P.stop("manual") end
    end
    imgui.text("Samples " .. #P.samples .. "; peak " .. string.format("%.2f", P.peak_ms) .. " ms")
    imgui.text(P.status or "Load a quiet Grace gameplay scene, then Find Grace candidate")
    end)
    if not ok then diagnostic("UI: " .. tostring(err)); P.status = "UI error; inspect diagnostics" end
    imgui.tree_pop()
end
-- Dependencies are checked before callback registration. A missing dependency stays visible
-- in the returned object; no engine operations are attempted from an incomplete runtime.
P.dependencies()
if re and type(re.on_frame) == "function" then re.on_frame(P.frame) end
if re and type(re.on_draw_ui) == "function" then re.on_draw_ui(draw) end
BelaBindingProbeV5 = P
return P

