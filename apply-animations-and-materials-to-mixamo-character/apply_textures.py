import bpy
import os

# ============================================================
# SPECIAL OPS CLOTHING - PBR TEXTURE IMPORTER
# Blender 4.3+
# ============================================================

# ------------------------------------------------------------
# 1. TEXTURE DIRECTORY
# ------------------------------------------------------------

TEXTURE_DIR = r"D:\special-ops\models\specialist\textures"


# ------------------------------------------------------------
# 2. TEXTURE SET NAMES
# ------------------------------------------------------------

TEXTURE_SETS = {
    "blues and stretch": "forsub_blues and stretch",
    "buckle":            "forsub_buckle",
    "glove":             "forsub_glove",
    "glove_dical":       "forsub_glove_dical",
    "hats and masks":    "forsub_hats and masks",
    "hoodie":            "forsub_hoodie",
    "pants":             "forsub_pants",
    "strap":             "forsub_strap",
    "zipper":            "forsub_zipper",
}


# ------------------------------------------------------------
# 3. TEMPORARY COLOR -> TEXTURE SET MAPPING
#
# These correspond to the TEXTURE_TEST materials from the
# previous diagnostic.
#
# 01 and 02 are the two tiny pieces. If they are reversed,
# simply swap "buckle" and "glove_dical" below.
# ------------------------------------------------------------

TEST_TO_TEXTURE = {
    "TEXTURE_TEST_01": "buckle",
    "TEXTURE_TEST_02": "glove_dical",

    "TEXTURE_TEST_03": "hoodie",
    "TEXTURE_TEST_04": "zipper",
    "TEXTURE_TEST_05": "strap",
    "TEXTURE_TEST_06": "blues and stretch",
    "TEXTURE_TEST_07": "pants",
    "TEXTURE_TEST_08": "glove",
    "TEXTURE_TEST_09": "hats and masks",
}


# ------------------------------------------------------------
# 4. FILE FINDER
# ------------------------------------------------------------

def find_texture(prefix, suffix):
    """
    Find a texture such as:

    forsub_hoodie_BaseColor.png
    forsub_hoodie_Roughness.png
    etc.
    """

    filename = f"{prefix}_{suffix}.png"
    path = os.path.join(TEXTURE_DIR, filename)

    if os.path.exists(path):
        return path

    return None


# ------------------------------------------------------------
# 5. LOAD IMAGE
# ------------------------------------------------------------

def load_image(path):
    if not path:
        return None

    # Reuse already-loaded Blender image if possible
    existing = bpy.data.images.get(os.path.basename(path))

    if existing:
        return existing

    try:
        return bpy.data.images.load(path, check_existing=True)
    except Exception as e:
        print("ERROR loading:", path)
        print(e)
        return None


# ------------------------------------------------------------
# 6. CREATE PBR MATERIAL
# ------------------------------------------------------------

def create_pbr_material(texture_name):

    prefix = TEXTURE_SETS[texture_name]

    mat_name = f"PBR_{texture_name}"

    # Remove/replace old material with same name
    mat = bpy.data.materials.get(mat_name)

    if mat is None:
        mat = bpy.data.materials.new(mat_name)

    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    # --------------------------------------------------------
    # Nodes
    # --------------------------------------------------------

    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = "Material Output"
    output.location = (700, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Principled BSDF"
    bsdf.location = (400, 0)

    links.new(
        bsdf.outputs["BSDF"],
        output.inputs["Surface"]
    )

    # --------------------------------------------------------
    # Base Color
    # --------------------------------------------------------

    base_path = find_texture(prefix, "BaseColor")

    if base_path:
        tex = nodes.new("ShaderNodeTexImage")
        tex.name = "Base Color"
        tex.label = "BASE COLOR"
        tex.location = (-600, 250)

        tex.image = load_image(base_path)

        # Correct color space
        if tex.image:
            tex.image.colorspace_settings.name = "sRGB"

        links.new(
            tex.outputs["Color"],
            bsdf.inputs["Base Color"]
        )

    # --------------------------------------------------------
    # Roughness
    # --------------------------------------------------------

    rough_path = find_texture(prefix, "Roughness")

    if rough_path:
        tex = nodes.new("ShaderNodeTexImage")
        tex.name = "Roughness"
        tex.label = "ROUGHNESS"
        tex.location = (-600, 0)

        tex.image = load_image(rough_path)

        if tex.image:
            tex.image.colorspace_settings.name = "Non-Color"

        links.new(
            tex.outputs["Color"],
            bsdf.inputs["Roughness"]
        )

    # --------------------------------------------------------
    # Metallic
    # --------------------------------------------------------

    metallic_path = find_texture(prefix, "Metallic")

    if metallic_path:
        tex = nodes.new("ShaderNodeTexImage")
        tex.name = "Metallic"
        tex.label = "METALLIC"
        tex.location = (-600, -200)

        tex.image = load_image(metallic_path)

        if tex.image:
            tex.image.colorspace_settings.name = "Non-Color"

        links.new(
            tex.outputs["Color"],
            bsdf.inputs["Metallic"]
        )

    # --------------------------------------------------------
    # NORMAL MAP
    # --------------------------------------------------------

    normal_path = find_texture(prefix, "Normal")

    if normal_path:

        tex = nodes.new("ShaderNodeTexImage")
        tex.name = "Normal Texture"
        tex.label = "NORMAL"
        tex.location = (-600, -400)

        tex.image = load_image(normal_path)

        if tex.image:
            tex.image.colorspace_settings.name = "Non-Color"

        normal = nodes.new("ShaderNodeNormalMap")
        normal.name = "Normal Map"
        normal.location = (100, -250)

        links.new(
            tex.outputs["Color"],
            normal.inputs["Color"]
        )

        links.new(
            normal.outputs["Normal"],
            bsdf.inputs["Normal"]
        )

    # --------------------------------------------------------
    # HEIGHT -> BUMP
    # --------------------------------------------------------

    height_path = find_texture(prefix, "Height")

    if height_path:

        tex = nodes.new("ShaderNodeTexImage")
        tex.name = "Height"
        tex.label = "HEIGHT"
        tex.location = (-600, -600)

        tex.image = load_image(height_path)

        if tex.image:
            tex.image.colorspace_settings.name = "Non-Color"

        bump = nodes.new("ShaderNodeBump")
        bump.name = "Height Bump"
        bump.location = (100, -450)

        bump.inputs["Strength"].default_value = 0.20
        bump.inputs["Distance"].default_value = 0.05

        links.new(
            tex.outputs["Color"],
            bump.inputs["Height"]
        )

        links.new(
            bump.outputs["Normal"],
            bsdf.inputs["Normal"]
        )

    # --------------------------------------------------------
    # GENERAL MATERIAL SETTINGS
    # --------------------------------------------------------

    if "Roughness" not in bsdf.inputs:
        pass

    # Nice default if texture is missing
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.5

    return mat


# ------------------------------------------------------------
# 7. CREATE ALL MATERIALS
# ------------------------------------------------------------

print("\n")
print("================================================")
print("SPECIAL OPS PBR TEXTURE IMPORT")
print("================================================")
print("Texture directory:")
print(TEXTURE_DIR)
print("================================================")

materials = {}

for texture_name in TEXTURE_SETS:

    print("\nCreating:", texture_name)

    mat = create_pbr_material(texture_name)

    materials[texture_name] = mat

    print("  Material:", mat.name)


# ------------------------------------------------------------
# 8. ASSIGN MATERIALS TO OBJECTS
# ------------------------------------------------------------

assignments = 0
unknown = []

print("\n")
print("================================================")
print("ASSIGNING MATERIALS")
print("================================================")

for obj in bpy.context.selected_objects:

    if obj.type != 'MESH':
        continue

    texture_name = None

    # --------------------------------------------------------
    # Find the temporary TEXTURE_TEST material
    # --------------------------------------------------------

    for slot in obj.material_slots:

        if not slot.material:
            continue

        old_name = slot.material.name

        if old_name in TEST_TO_TEXTURE:
            texture_name = TEST_TO_TEXTURE[old_name]
            break

    # --------------------------------------------------------
    # No test material found
    # --------------------------------------------------------

    if texture_name is None:
        unknown.append(obj.name)

        print(
            "SKIPPED:",
            obj.name,
            "(no TEXTURE_TEST material found)"
        )

        continue

    # --------------------------------------------------------
    # Assign final PBR material
    # --------------------------------------------------------

    final_mat = materials[texture_name]

    if obj.material_slots:

        # Replace the first slot
        obj.material_slots[0].material = final_mat

        # Remove any additional old material slots
        while len(obj.material_slots) > 1:
            obj.data.materials.pop(
                index=len(obj.data.materials) - 1
            )

    else:
        obj.data.materials.append(final_mat)

    assignments += 1

    print(
        "ASSIGNED:",
        obj.name,
        "->",
        texture_name
    )


# ------------------------------------------------------------
# 9. REPORT
# ------------------------------------------------------------

print("\n")
print("================================================")
print("IMPORT COMPLETE")
print("================================================")

print("Texture sets:", len(TEXTURE_SETS))
print("Objects assigned:", assignments)

if unknown:

    print("\nOBJECTS NOT ASSIGNED:")

    for name in unknown:
        print("  ", name)

else:

    print("All selected clothing objects assigned.")

print("\nMaterials created:")

for name in materials:
    print("  PBR_" + name)

print("================================================")
print("DONE")
print("================================================")