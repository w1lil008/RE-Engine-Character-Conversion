"""Compare Blender's deformed triangle corners against original glTF LBS."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import json
import argparse
import math
import numpy as np
import bpy
from mathutils import Matrix
from common import ROOT,confined,write_json
from glb_read import load,accessor,sample_globals

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--config',default='config/source_idle_v0.2.0.json')
p.add_argument('--output');p.add_argument('--report-name',default='source_idle')
args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
if not args.report_name.replace('_','').isalnum():raise ValueError('Invalid report name')
config=json.loads(confined(ROOT,args.config).read_text());out=confined(ROOT,args.output or config['output'])
frames=sorted(set(int(config['frames']*fraction) for fraction in [0,.25,.5,.75,1]))
bpy.ops.wm.open_mainfile(filepath=str(out/'source_idle.blend'))
doc,data=load(out/'source_idle.glb');axis=np.asarray(Matrix.Rotation(math.pi/2,4,'X'))
skin=doc['skins'][0];inverse=accessor(doc,data,skin['inverseBindMatrices']).reshape(-1,4,4).swapaxes(-1,-2)
records=[]
for frame in frames:
    bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    transforms=sample_globals(doc,data,frame/config['fps'])[skin['joints']] @ inverse
    for node in doc['nodes']:
        if 'mesh' not in node:continue
        expected=[]
        for p in doc['meshes'][node['mesh']]['primitives']:
            attrs=p['attributes'];v=accessor(doc,data,attrs['POSITION']);vh=np.c_[v,np.ones(len(v))];deformed=np.zeros((len(v),4))
            for suffix in ['0','1']:
                if 'WEIGHTS_'+suffix not in attrs:continue
                w=accessor(doc,data,attrs['WEIGHTS_'+suffix]);j=accessor(doc,data,attrs['JOINTS_'+suffix])
                for k in range(4):deformed+=np.einsum('nij,nj->ni',transforms[j[:,k]],vh)*w[:,k,None]
            points=(axis @ deformed.T).T[:,:3]
            expected.append(points[accessor(doc,data,p['indices']).reshape(-1)])
        expected=np.concatenate(expected)
        obj=bpy.data.objects[node['name']];evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
        actual=np.array([(evaluated.matrix_world @ mesh.vertices[i].co).to_tuple() for triangle in mesh.loop_triangles for i in triangle.vertices])
        if actual.shape!=expected.shape:raise ValueError('Triangle corner count changed on Blender import')
        errors=np.linalg.norm(actual-expected,axis=1);evaluated.to_mesh_clear()
        maximum=float(errors.max());records.append({'frame':frame,'component':node['name'],'corners':len(errors),'max_error_m':maximum,'mean_error_m':float(errors.mean())})
        if maximum>.0002:raise ValueError(f'Original geometry skinning mismatch: {records[-1]}')
write_json(ROOT/f'reports/animation_dev/{args.report_name}_skinning.json',{'status':'PASSED','frames':frames,
    'input_glb':(out/'source_idle.glb').relative_to(ROOT).as_posix(),
    'maximum_triangle_corner_error_m':max(r['max_error_m'] for r in records),'components':records,
    'scope':'All source body/face/hair/dress triangle corners, all eight influences where present, original inverse binds; independent CPU LBS versus Blender evaluated geometry.'})
print('Original source geometry skinning comparisons passed')

