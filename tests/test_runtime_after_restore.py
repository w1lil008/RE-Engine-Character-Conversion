import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/runtime-probe-deps'));sys.path.insert(0,str(ROOT/'tests'))
from lupa.lua54 import LuaRuntime
from test_runtime_preparation import to_python

MOCK='''
fixture_time=0;fixture_files={};fixture_methods={}
os.clock=function()return fixture_time end;os.time=function()return fixture_time end
local returns={get_RootMotion='via.motion.RootPlayMode',get_RootMotionTranslation='via.vec3',
 get_OriginalRootMotionTranslation='via.vec3',get_RootMotionRotation='via.Quaternion',get_OriginalRootMotionRotation='via.Quaternion'}
local definitions={}
for name,ret in pairs(returns)do
 local n,r=name,ret
 definitions[#definitions+1]={get_name=function()return n end,is_static=function()return false end,
  get_param_types=function()return {}end,get_return_type=function()return {get_full_name=function()return r end}end,
  call=function() fixture_methods[#fixture_methods+1]=n;if r=='via.motion.RootPlayMode' then return 2 end;return {x=0,y=0,z=0,w=1}end}
end
fixture_definition={get_methods=function()return definitions end,get_parent_type=function()return nil end}
fixture_motion={get_type_definition=function()return fixture_definition end}
fixture_probe={watches={{motion=fixture_motion,selection={name='cp_A100',joint_count=80}}},
 clear=function()return true end,prepare=function()return true end}
fixture_probe.start=function()fixture_probe.running=true;return true end
fixture_probe.stop=function()fixture_probe.running=false;fixture_probe.saved_path='bela_d2/fixture.json';return true end
dofile=function()return fixture_probe end
sdk={get_tdb_version=function()return 83 end}
reframework={get_game_name=function()return 're9'end,get_commit_hash=function()return 'd1461375aee4ec3f313170f8eaad12064eb542d9'end}
re={on_frame=function(f)fixture_frame=f end}
fs={glob=function()local a={};for k in pairs(fixture_files)do a[#a+1]=k end;return a end,read=function(k)return fixture_files[k]end}
json={dump_string=function(v,n)return fixture_encode(v,n)end,dump_file=function(k,v,n)fixture_files[k]=fixture_encode(v,n);return true end}
'''

class AfterRestoreTests(unittest.TestCase):
    def runtime(self,setup=''):
        lua=LuaRuntime();lua.globals().fixture_encode=lambda d,n:json.dumps(to_python(d),indent=n)
        lua.execute(MOCK);lua.execute(setup)
        factory=lua.execute((ROOT/'scripts/runtime/bela_after_restore.lua').read_text())
        factory(lua.table_from({'session':'after_restore_fixture','probe_path':'fixture.lua'}))
        return lua

    def test_delayed_read_only_capture_and_verified_json_save(self):
        lua=self.runtime();lua.execute('fixture_time=7;fixture_frame()')
        self.assertEqual(lua.eval('#fixture_methods'),0)
        lua.execute('fixture_time=8;fixture_frame();fixture_probe.stop();fixture_frame()')
        self.assertEqual(lua.eval('BelaAfterRestore.phase'),'COMPLETE')
        self.assertEqual(lua.eval('#BelaAfterRestore.rows'),1)
        doc=json.loads(lua.eval('fixture_files["bela_runtime_test/after_restore_fixture_after_restore.json"]'))
        self.assertTrue(doc['read_only']);self.assertEqual(doc['binding_capture_path'],'bela_d2/fixture.json')
        self.assertEqual(set(to_python(lua.eval('fixture_methods'))),{'get_RootMotion','get_RootMotionTranslation','get_OriginalRootMotionTranslation','get_RootMotionRotation','get_OriginalRootMotionRotation'})

    def test_unavailable_exact_api_stops_without_inventing_a_result(self):
        lua=self.runtime('fixture_definition.get_methods=function()return {}end')
        lua.execute('fixture_time=8;fixture_frame();fixture_time=50;fixture_frame()')
        self.assertEqual(lua.eval('BelaAfterRestore.phase'),'FAILED')
        self.assertFalse(lua.eval('fixture_probe.running'))
        self.assertEqual(lua.eval('#BelaAfterRestore.errors'),1)
        self.assertEqual(lua.eval('#fixture_methods'),0)

    def test_existing_capture_cannot_be_overwritten(self):
        lua=self.runtime('fixture_files["bela_runtime_test/after_restore_fixture_after_restore.json"]="previous evidence"')
        lua.execute('fixture_time=8;fixture_frame();fixture_probe.stop();fixture_frame()')
        self.assertEqual(lua.eval('BelaAfterRestore.phase'),'FAILED')
        self.assertEqual(lua.eval('fixture_files["bela_runtime_test/after_restore_fixture_after_restore.json"]'),'previous evidence')

if __name__=='__main__':unittest.main()

