-- A mocked engine, explicitly not live RE9 evidence.
local now, wall = 0, 0
local calls, frames, motions = {}, 0, 0
local writes, last_doc, registrations = 0, nil, 0
os.clock = function() return now end
os.time = function() return wall end
os.date = function() return "20261010T000000Z" end
local function def(name, methods, fields)
    local d = {name = name, methods = {}, fields = fields or {}}
    function d:get_full_name() return self.name end
    function d:get_parent_type() return nil end
    function d:get_fields() return self.fields end
    function d:get_methods() return self.methods end
    function d:get_method(n) for _, m in ipairs(self.methods) do if m.name == n then return m end end end
    for n, spec in pairs(methods) do
        local m = {name = n, spec = spec}
        function m:get_name() return self.name end
        function m:get_num_params() return #self.spec.params end
        function m:get_param_types()
            local t = {}; for _, p in ipairs(self.spec.params) do t[#t + 1] = def(p, {}) end; return t
        end
        function m:get_return_type() return def(self.spec.returns or "System.Int32", {}) end
        function m:is_static() return self.spec.static == true end
        function m:call(obj, ...)
            calls[#calls + 1] = self.name
            return self.spec.fn(obj, ...)
        end
        d.methods[#d.methods + 1] = m
    end
    return d
end
local function getter(value, params, static)
    return {params = params or {}, static = static,
        fn = type(value) == "function" and value or function() return value end}
end
local function obj(d)
    local o = {}
    function o:get_type_definition() return d end
    function o:get_address() return 42 end
    function o:get_field() return nil end
    return o
end
local function array(list)
    return {get_size = function() return #list end, get_element = function(self, i) return list[i + 1] end}
end
local list = obj(def("via.motion.MotionListResource", {ToString = getter("via.motion.MotionListResource[Animation/ch/ch02/ch0200/motlist/ch0200_GeneralM.motlist]")}))
local bank = obj(def("via.motion.MotionBank", {get_BankID = getter(0), get_BankType = getter(0),
    get_BankTypeMask = getter(0), get_MotionList = getter(list)}))
local node = obj(def("via.motion.MotionNode", {get_MotionID = getter(function() return motions end),
    get_MotionBankID = getter(0), get_MotionName = getter("original idle"), get_SwitchValue = getter(0),
    get_Frame = getter(function() return frames end), get_JointMaskID = getter(0),
    -- These exist in reflection, but must never be executed.
    set_Frame = getter(function() error("ENGINE WRITE") end, {"System.Single"}),
    get_State = getter(function() error("Static getter called") end, {}, true),
    get_Speed = getter(function() error("Wrong arity getter called") end, {"System.Int32"})}))
local layer = obj(def("via.motion.MotionLayer", {getMotionNode = getter(node, {"System.UInt32"}),
    getMotionNodeCount = getter(1), get_Frame = getter(function() return frames end), get_Weight = getter(1)}))
local go = obj(def("via.GameObject", {get_Name = getter("cp_A100_fixture"), get_Components = getter(array({}))}))
local motion = obj(def("via.motion.Motion", {get_GameObject = getter(go), get_JointCount = getter(611),
    getLayerCount = getter(1), getLayer = getter(layer, {"System.UInt32"}), get_ActiveMotionBank = getter(array({bank}))}))
local scene = obj(def("via.Scene", {findComponents = getter(array({motion}), {"System.Type"})}))
local manager_def = def("via.SceneManager", {get_CurrentScene = getter(scene)})
sdk = {
    get_tdb_version = function() return 83 end,
    find_type_definition = function(n) if n == "via.SceneManager" then return manager_def elseif n == "via.motion.Motion" then return motion:get_type_definition() end end,
    get_native_singleton = function() return {} end,
    call_native_func = function(o, d, n) assert(n == "get_CurrentScene"); calls[#calls + 1] = n; return scene end,
    typeof = function() return {} end
}
reframework = {get_game_name = function() return "re9" end,
    get_commit_hash = function() return "d1461375aee4ec3f313170f8eaad12064eb542d9" end}
re = {on_frame = function(fn) fixture_frame = fn; registrations = registrations + 1 end, on_draw_ui = function(fn) fixture_ui = fn end}
json = {dump_file = function(path, doc)
    assert(path:find("^bela_d1/") and not path:find("%.%.")); writes = writes + 1; last_doc = doc; return true
end}
function fixture_advance(t, frame, motion_id)
    now = now + t; wall = math.floor(now); frames = frame or frames; motions = motion_id or motions
    fixture_frame()
end
function fixture_fail_getter()
    for _, m in ipairs(node:get_type_definition():get_methods()) do
        if m.name == "get_MotionName" then m.spec.fn = function() error("fixture getter failure") end end
    end
end
function fixture_result() return {calls = calls, writes = writes, doc = last_doc, registrations = registrations} end

