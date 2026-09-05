# Blender animation merge tutorial

Original code and tutorial instructions were made by [Hai](https://github.com/HaiTheDev)

## Tutorial

1)  Create new Blender file. File -> Import -> FBX -> original Specialist model .FBX
2)  Select the 9 clothing meshes. Run apply_materials.py, then apply_textures.py & fix pants
3)  Save as AtlasMesh.blend, run combine_meshes_atlas.py
4)  Delete the original armature / Empty / 9-material clothing meshes
5)  Export the Mixamo upload rig as atlas_for_mixamo.FBX
6)  mixamo.com -> Upload Character -> atlas_for_mixamo.FBX
7)  Place markers, Skinning: Standard, finish the auto-rigger
8)  Download animations from THIS character, FBX, With Skin, In Place, 30 fps
9)  Put them in a folder (e.g. animations\working-latest)
8)  New Blender file "combined_animations_with_skin.blend", run combine_fbx_nla.py
9)  Set ANIM_DIR to that folder, Run Script.
10) It writes working-latest.blend + combined_animations_with_skin.glb with NLA tracks.
