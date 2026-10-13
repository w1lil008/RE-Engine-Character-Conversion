import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/runtime-probe-deps'));sys.path.insert(0,str(ROOT/'tests'))
from lupa.lua54 import LuaRuntime
from test_runtime_preparation import to_python

class OneCycleTests(unittest.TestCase):
    def runtime(self,setup=''):
        lua=LuaRuntime();lua.globals().fixture_encode=lambda d,n:json.dumps(to_python(d),indent=n)
        lua.execute((ROOT/'tests/runtime_one_cycle_fixture.lua').read_text())
        lua.execute(setup)
        module=lua.execute((ROOT/'scripts/runtime/bela_one_cycle.lua').read_text())
        module(lua.globals().fixture_config)
        return lua

    def test_zero_weight_test_restores_counts_and_preserves_original_idle(self):
        lua=self.runtime();lua.execute('fixture_advance(0);fixture_advance(.1);fixture_advance(2.0);fixture_advance(5.1)')
        self.assertEqual(lua.eval('BelaOneCycle.phase'),'COMPLETE')
        self.assertFalse(lua.eval('BelaOneCycle.bound or BelaOneCycle.playback'))
        self.assertEqual(lua.eval('fixture_motion.layer_count'),17)
        self.assertEqual(lua.eval('fixture_motion.bank_count'),3)
        self.assertTrue(lua.eval('fixture_motion.layers[0]==fixture_original'))
        self.assertEqual(lua.eval('#BelaOneCycle.errors'),0)

    def test_one_cycle_requires_live_cleanup_gate_before_any_mutation(self):
        with self.assertRaises(Exception):self.runtime('fixture_config.mode="one_cycle"')

    def test_validated_cycle_finishes_at_300_and_restores_original_references(self):
        lua=self.runtime('fixture_config.mode="one_cycle";fixture_config.gates.live_zero_weight_cleanup=true')
        lua.execute('fixture_advance(0);fixture_advance(.1);fixture_advance(2.0);fixture_advance(0);fixture_advance(5);fixture_advance(5.1)')
        self.assertEqual(lua.eval('BelaOneCycle.phase'),'COMPLETE')
        self.assertTrue(lua.eval('BelaOneCycle.playback'))
        self.assertFalse(lua.eval('BelaOneCycle.bound'))
        self.assertEqual(lua.eval('fixture_motion.layer_count'),17)
        self.assertTrue(lua.eval('fixture_motion.layers[0]==fixture_original'))

    def test_missing_joint_aborts_before_visible_playback_and_restores(self):
        lua=self.runtime('fixture_config.mode="one_cycle";fixture_config.gates.live_zero_weight_cleanup=true;fixture_missing_joint=true')
        lua.execute('fixture_advance(0);fixture_advance(.1);fixture_advance(5.1)')
        self.assertFalse(lua.eval('BelaOneCycle.playback or BelaOneCycle.bound'))
        self.assertEqual(lua.eval('fixture_motion.layer_count'),17)
        self.assertEqual(lua.eval('#BelaOneCycle.errors'),1)

    def test_stalled_native_frame_has_bounded_deadline(self):
        lua=self.runtime('fixture_config.mode="one_cycle";fixture_config.gates.live_zero_weight_cleanup=true')
        lua.execute('fixture_advance(0);fixture_advance(.1);fixture_advance(2.0);fixture_advance(0);fixture_time=fixture_time+7;fixture_frame()')
        self.assertFalse(lua.eval('BelaOneCycle.bound'))
        events=to_python(lua.eval('BelaOneCycle.events'))
        self.assertTrue(any(e.get('data',{}).get('reason')=='Playback deadline reached before frame 300' for e in events))

    def test_loop_wrap_detaches_without_playing_a_second_cycle(self):
        lua=self.runtime('fixture_config.mode="one_cycle";fixture_config.gates.live_zero_weight_cleanup=true')
        lua.execute('fixture_advance(0);fixture_advance(.1);fixture_advance(2);fixture_advance(0);fixture_advance(4.98);fixture_motion.layers[17].frame=.2;fixture_frame()')
        self.assertFalse(lua.eval('BelaOneCycle.bound'))
        self.assertEqual(lua.eval('fixture_motion.layer_count'),17)
        events=to_python(lua.eval('BelaOneCycle.events'))
        self.assertTrue(any(e.get('data',{}).get('reason')=='One native cycle completed at first loop wrap' for e in events))

    def test_preview_countdown_keeps_layer_nonvisible(self):
        lua=self.runtime('fixture_config.mode="one_cycle";fixture_config.gates.live_zero_weight_cleanup=true;fixture_config.preview_delay_seconds=12')
        lua.execute('fixture_advance(0);fixture_advance(.1);fixture_advance(2);fixture_advance(10)')
        self.assertEqual(lua.eval('BelaOneCycle.phase'),'ARMED_FOR_ONE_CYCLE')
        self.assertFalse(lua.eval('BelaOneCycle.playback'))
        self.assertEqual(lua.eval('BelaOneCycle.layer.weight'),0)
        lua.execute('fixture_advance(2)')
        self.assertTrue(lua.eval('BelaOneCycle.playback'))

    def test_long_countdown_reserves_pose_budget_for_playback(self):
        lua=self.runtime('fixture_config.mode="one_cycle";fixture_config.gates.live_zero_weight_cleanup=true;fixture_config.preview_delay_seconds=12')
        lua.execute('fixture_advance(0);fixture_advance(.1);fixture_advance(2);for i=1,239 do fixture_advance(.05) end')
        self.assertLess(lua.eval('#BelaOneCycle.poses'),10)
        lua.execute('fixture_advance(.1);for i=1,101 do fixture_advance(.05) end;fixture_advance(5.1)')
        self.assertEqual(lua.eval('BelaOneCycle.phase'),'COMPLETE')
        self.assertGreater(lua.eval('#BelaOneCycle.poses'),90)
        self.assertEqual(lua.eval('#BelaOneCycle.errors'),0)

    def test_upper_body_interrupt_aborts_even_when_base_idle_is_unchanged(self):
        lua=self.runtime('fixture_config.mode="one_cycle";fixture_config.gates.live_zero_weight_cleanup=true;fixture_config.preview_delay_seconds=12')
        lua.execute('fixture_advance(0);fixture_advance(.1);fixture_advance(2);fixture_motion.layers[3].id=2;fixture_advance(.1)')
        self.assertFalse(lua.eval('BelaOneCycle.bound or BelaOneCycle.playback'))
        self.assertEqual(lua.eval('fixture_original.id'),1)
        self.assertEqual(lua.eval('fixture_motion.layers[3].id'),2)
        events=to_python(lua.eval('BelaOneCycle.events'))
        self.assertTrue(any(e.get('data',{}).get('reason')=='Original state interrupted on layer 3' for e in events))

    def test_movement_interrupt_cleans_up_without_forcing_controller_back_to_idle(self):
        lua=self.runtime('fixture_config.mode="one_cycle";fixture_config.gates.live_zero_weight_cleanup=true;fixture_config.preview_delay_seconds=12')
        lua.execute('fixture_advance(0);fixture_advance(.1);fixture_advance(2);fixture_interrupt=true;fixture_advance(.1);fixture_advance(5.1)')
        self.assertEqual(lua.eval('BelaOneCycle.phase'),'COMPLETE')
        self.assertFalse(lua.eval('BelaOneCycle.bound or BelaOneCycle.playback'))
        self.assertEqual(lua.eval('fixture_original.id'),2)
        self.assertEqual(lua.eval('fixture_motion.layer_count'),17)
        self.assertEqual(lua.eval('fixture_motion.bank_count'),3)
        self.assertEqual(lua.eval('#BelaOneCycle.errors'),0)

if __name__=='__main__':unittest.main()

