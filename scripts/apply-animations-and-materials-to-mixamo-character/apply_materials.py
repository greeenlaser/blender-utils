import bpy

# ============================================================
# SPECIAL OPS - PREPARE TEXTURE TEST MATERIALS
# Run this BEFORE the PBR TEXTURE IMPORTER
# ============================================================

# ------------------------------------------------------------
# COLORS
# ------------------------------------------------------------

colors = [
    (1.0, 0.0, 0.0, 1.0),  # 01 RED
    (0.0, 1.0, 0.0, 1.0),  # 02 GREEN
    (0.0, 0.2, 1.0, 1.0),  # 03 BLUE
    (1.0, 0.8, 0.0, 1.0),  # 04 YELLOW
    (1.0, 0.0, 1.0, 1.0),  # 05 MAGENTA
    (0.0, 1.0, 1.0, 1.0),  # 06 CYAN
    (1.0, 0.3, 0.0, 1.0),  # 07 ORANGE
    (0.5, 0.0, 1.0, 1.0),  # 08 PURPLE
    (0.0, 1.0, 0.3, 1.0),  # 09 MINT
]

# ------------------------------------------------------------
# GET SELECTED MESHES
# ------------------------------------------------------------

selected = [
    obj for obj in bpy.context.selected_objects
    if obj.type == 'MESH'
]

print("\n")
print("================================================")
print("PREPARING TEXTURE TEST MATERIALS")
print("================================================")

print("Selected meshes:", len(selected))

if len(selected) != 9:
    print("")
    print("WARNING!")
    print("Expected exactly 9 clothing meshes.")
    print("Found:", len(selected))
    print("")
    print("Select all 9 clothing meshes and run again.")
    print("================================================")

else:

    # --------------------------------------------------------
    # REMOVE OLD TEST MATERIALS
    # --------------------------------------------------------

    for i in range(1, 10):

        name = f"TEXTURE_TEST_{i:02d}"

        old = bpy.data.materials.get(name)

        if old:
            bpy.data.materials.remove(old)

    # --------------------------------------------------------
    # SORT OBJECTS
    #
    # This makes the assignment deterministic rather than
    # depending on the order in which Blender happens to
    # return selected objects.
    # --------------------------------------------------------

    selected.sort(key=lambda obj: obj.name)

    # --------------------------------------------------------
    # CREATE AND ASSIGN TEST MATERIALS
    # --------------------------------------------------------

    for i, obj in enumerate(selected):

        color = colors[i]

        mat_name = f"TEXTURE_TEST_{i+1:02d}"

        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True

        mat.diffuse_color = color

        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")

        if bsdf:

            bsdf.inputs["Base Color"].default_value = color

            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = color

            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = 1.0

            bsdf.inputs["Roughness"].default_value = 0.5

        # ----------------------------------------------------
        # Remove existing material slots
        # ----------------------------------------------------

        obj.data.materials.clear()

        # Add temporary test material
        obj.data.materials.append(mat)

        print(
            f"TEXTURE_TEST_{i+1:02d}",
            "->",
            obj.name
        )

    # --------------------------------------------------------
    # FINAL MAPPING
    # --------------------------------------------------------

    print("")
    print("================================================")
    print("TEXTURE MAPPING")
    print("================================================")

    print("01 -> buckle")
    print("02 -> glove_dical")
    print("03 -> hoodie")
    print("04 -> zipper")
    print("05 -> strap")
    print("06 -> blues and stretch")
    print("07 -> pants")
    print("08 -> glove")
    print("09 -> hats and masks")

    print("")
    print("================================================")
    print("PREPARATION COMPLETE")
    print("================================================")
    print("Now run the PBR TEXTURE IMPORTER.")
    print("================================================")

    # --------------------------------------------------------
    # Force Material Preview
    # --------------------------------------------------------

    for area in bpy.context.screen.areas:

        if area.type == 'VIEW_3D':

            area.spaces.active.shading.type = 'MATERIAL'