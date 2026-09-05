"""Import every Mixamo-with-skin FBX from a folder into one .blend with NLA tracks.

Each FBX is a full character. This keeps the first rig + meshes, copies every
clip onto that armature as a named Action + NLA strip, and deletes the duplicates.

In Blender: Text -> Open this file from disk, then Text -> Reload if it was
already open, then Run Script.

Or from a terminal:

  blender --background --python tools/combine_fbx_nla.py
"""

import sys
from pathlib import Path

import bpy

TOOLS_DIR = Path(r"D:\special-ops\tools")
ANIM_DIR = Path(r"D:\special-ops\animations\working-latest")
OUTPUT_BLEND = Path(r"D:\special-ops\tools\working-latest.blend")

sys.path.insert(0, str(TOOLS_DIR))
import merge_mixamo_armatures as mixamo  # noqa: E402


def clear_scene():
    mixamo.object_mode()
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    mixamo.purge_unused()


def save_blend(path):
    path = Path(path).expanduser().resolve()
    if path.suffix.lower() != ".blend":
        path = path.with_suffix(".blend")
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print("Saved %s (%s bytes)" % (path, path.stat().st_size))


def main():
    anim_dir = ANIM_DIR
    output_blend = OUTPUT_BLEND
    if "--" in sys.argv:
        extra = sys.argv[sys.argv.index("--") + 1 :]
        if "--anim-dir" in extra:
            anim_dir = Path(extra[extra.index("--anim-dir") + 1])
        if "--output" in extra:
            output_blend = Path(extra[extra.index("--output") + 1])

    if not anim_dir.is_dir():
        raise FileNotFoundError(anim_dir)

    print("Clearing scene, importing FBX from %s" % anim_dir)
    clear_scene()
    mixamo.import_anim_dir(anim_dir)

    armatures = mixamo.armature_objects()
    if not armatures:
        raise RuntimeError("No armatures imported from %s" % anim_dir)

    keeper, clips = mixamo.merge([], "")
    if not clips:
        raise RuntimeError("Imported armatures but found no pose clips")

    print("NLA tracks on %s:" % keeper.name)
    for name, action in clips:
        start, end = mixamo.frame_range(action)
        print("  %s: frames %s-%s" % (name, start, end))

    mixamo.force_opaque_materials()
    save_blend(output_blend)
    mixamo.export_glb(output_blend.with_suffix(".glb"), keeper)


if __name__ == "__main__":
    main()
