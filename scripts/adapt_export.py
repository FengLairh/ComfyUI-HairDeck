"""Port the upstream Linux wrapper/worker export to portable one-shot Blender calls."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
path = root / '_vendor/hairdeck_core/vrm/export.py'
text = path.read_text(encoding='utf-8')
text = text.replace("SCRIPTS = os.path.join(RELEASE, 'blender')", "SCRIPTS = os.path.join(RELEASE, 'blender_scripts')")
text = re.sub(r'def blender_cmd\(\):.*?(?=def work_dir)',
              '''def blender_cmd():
    command = paths.get('blender')
    if not command:
        raise RuntimeError('A Blender 4.2 LTS executable must be configured.')
    return [command]


''', text, flags=re.S)
text = re.sub(r'def start_worker\(.*?(?=def _env)',
              '''def _blender(prep, d, body, timeout=300):
    cmd = blender_cmd() + ['-b', '--python', os.path.join(SCRIPTS, 'vrm_export.py'), '--', B.body_path(body), prep, d]
    return _run(cmd, f'{d}/blender.log', _env(False)), 'one-shot'


''', text, flags=re.S)
text = re.sub(r'def _env\(gl=True\):.*?(?=def _run)', '''def _env(gl=True):
    e = dict(os.environ)
    e.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONNOUSERSITE='1', HAIRDECK_NATIVE_ROOT=paths.get('root'))
    vendor = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    e['PYTHONPATH'] = vendor
    tools = os.path.join(paths.get('root'), 'tools', 'blender')
    resources = os.path.join(tools, 'user')
    e.update(BLENDER_USER_RESOURCES=resources, BLENDER_USER_CONFIG=os.path.join(resources, 'config'),
             BLENDER_USER_SCRIPTS=os.path.join(resources, 'scripts'), BLENDER_USER_DATAFILES=os.path.join(resources, 'datafiles'),
             BLENDER_USER_EXTENSIONS=os.path.join(resources, 'extensions'), BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION='true')
    if gl:
        import imageio_ffmpeg
        e['HAIRDECK_FFMPEG'] = imageio_ffmpeg.get_ffmpeg_exe()
        if os.name == 'nt':
            e.pop('PYOPENGL_PLATFORM', None)
        else:
            e['PYOPENGL_PLATFORM'] = 'egl'
    return e


''', text, flags=re.S)
text = text.replace("[sys.executable, '-m', 'hairdeck_core.vrm.render'", "[sys.executable, os.path.join(os.path.dirname(RELEASE), 'scripts', 'render_entry.py'), 'vrm'")
text = text.replace("[sys.executable, '-m', 'hairdeck_core.vis.turn_preview'", "[sys.executable, os.path.join(os.path.dirname(RELEASE), 'scripts', 'render_entry.py'), 'motion'")
text = text.replace("ref, orig = work_dir('ref', B.file_name('orig', bd)), f\"{d}/{B.file_name('orig', bd)}\"",
                    "ref = orig = f\"{d}/{B.file_name('orig', bd)}\"")
text = text.replace("patched = patch_render_queue(gen, ref) if how == 'worker' and os.path.exists(ref) else []",
                    "patched = patch_render_queue(gen, ref) if os.path.exists(ref) else []")
text = text.replace('timeout=timeout, cwd=RELEASE)', "timeout=timeout, cwd=RELEASE, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)")
path.write_text(text, encoding='utf-8', newline='\n')
for name in ['vis/turn_preview.py', 'vrm/render.py']:
    path = root / '_vendor/hairdeck_core' / name
    text = path.read_text(encoding='utf-8').replace("    os.environ.setdefault('PYOPENGL_PLATFORM', 'egl')", "    if os.name != 'nt':\n        os.environ.setdefault('PYOPENGL_PLATFORM', 'egl')")
    path.write_text(text, encoding='utf-8', newline='\n')
path = root / '_vendor/blender_scripts/vrm_export.py'
text = path.read_text(encoding='utf-8')
text = text.replace('    t1 = time.time()\n', '    E.export(arm, f"{out}/{B.file_name(\'orig\', bd)}")\n    t1 = time.time()\n')
path.write_text(text, encoding='utf-8', newline='\n')
