"""Join meshes and pack every material's Base Color into one atlas texture.

Does not use Cycles bake (that crashes Blender 4.5 on this character).
Each unique material gets a cell in a grid; UVs are remapped into that cell.

Run from Blender's Scripting tab (Text -> Open this file).
"""

from __future__ import annotations

from math import ceil, sqrt
from pathlib import Path

import bpy
import numpy as np

# --- config ---
ATLAS_SIZE = 4096
CELL_PAD = 8
MATERIAL_NAME = "Atlas"
OUTPUT_PNG = ""  # empty = next to the .blend as <blend>_atlas.png
USE_SELECTION = True  # False = every mesh in the file (skips icospheres)
KEEP_ORIGINALS = True


def object_mode() -> None:
    obj = bpy.context.view_layer.objects.active
    if obj is not None and obj.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def set_active(obj: bpy.types.Object) -> None:
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.hide_select = False
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def is_helper_mesh(obj: bpy.types.Object) -> bool:
    name = obj.name.split(".")[0].lower()
    return name in {"icosphere", "cube", "sphere"} and len(obj.data.vertices) <= 162


def source_meshes() -> list[bpy.types.Object]:
    selected = [o for o in bpy.context.selected_objects if o.type == "MESH" and not is_helper_mesh(o)]
    if USE_SELECTION and selected:
        return selected
    return [o for o in bpy.data.objects if o.type == "MESH" and not is_helper_mesh(o)]


def resolve_output() -> Path:
    if OUTPUT_PNG:
        path = Path(OUTPUT_PNG).expanduser()
        if not path.is_absolute():
            blend = Path(bpy.data.filepath).parent if bpy.data.filepath else Path.cwd()
            path = blend / path
        return path.with_suffix(".png")
    blend = bpy.data.filepath
    if blend:
        p = Path(blend)
        return p.with_name(p.stem + "_atlas.png")
    return Path.cwd() / "atlas.png"


def join_copies(meshes: list[bpy.types.Object]) -> bpy.types.Object:
    object_mode()
    copies: list[bpy.types.Object] = []
    for mesh in meshes:
        set_active(mesh)
        bpy.ops.object.duplicate()
        copy = bpy.context.view_layer.objects.active
        copy.name = mesh.name + "_atlas"
        copy.data = copy.data.copy()
        world = copy.matrix_world.copy()
        copy.parent = None
        copy.matrix_world = world
        set_active(copy)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        copies.append(copy)

    bpy.ops.object.select_all(action="DESELECT")
    for copy in copies:
        copy.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    if len(copies) > 1:
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = "AtlasMesh"
    return joined


def principled(mat: bpy.types.Material | None):
    if mat is None or not mat.use_nodes or mat.node_tree is None:
        return None
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def follow_color_node(node):
    seen = set()
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        if node.type == "TEX_IMAGE":
            return node
        color_in = next((i for i in node.inputs if i.type == "RGBA" and i.is_linked), None)
        if color_in is None:
            return node
        node = color_in.links[0].from_node
    return node


def basecolor_source(mat: bpy.types.Material | None) -> tuple[bpy.types.Image | None, tuple[float, float, float, float]]:
    fallback = (0.8, 0.8, 0.8, 1.0)
    bsdf = principled(mat)
    if bsdf is None:
        return None, fallback
    sock = bsdf.inputs.get("Base Color")
    if sock is None:
        return None, fallback
    color = tuple(sock.default_value)
    if not sock.is_linked:
        return None, color
    node = follow_color_node(sock.links[0].from_node)
    if node is not None and node.type == "TEX_IMAGE" and node.image is not None:
        image = node.image
        if image.size[0] == 0 or image.size[1] == 0:
            if image.filepath:
                image.reload()
        if image.size[0] > 0 and image.size[1] > 0:
            return image, color
    return None, color


def image_pixels(image: bpy.types.Image) -> np.ndarray:
    width, height = image.size
    channels = image.channels
    buf = np.empty(width * height * channels, dtype=np.float32)
    image.pixels.foreach_get(buf)
    arr = buf.reshape((height, width, channels))
    if channels == 3:
        alpha = np.ones((height, width, 1), dtype=np.float32)
        arr = np.concatenate([arr, alpha], axis=2)
    elif channels == 1:
        arr = np.repeat(arr, 4, axis=2)
        arr[:, :, 3] = 1.0
    return arr


def resize_nearest(arr: np.ndarray, width: int, height: int) -> np.ndarray:
    src_h, src_w = arr.shape[:2]
    ys = np.clip((np.arange(height) + 0.5) * src_h / height, 0, src_h - 1).astype(np.int32)
    xs = np.clip((np.arange(width) + 0.5) * src_w / width, 0, src_w - 1).astype(np.int32)
    return arr[ys[:, None], xs[None, :]]


def solid_image(color: tuple[float, float, float, float], width: int, height: int) -> np.ndarray:
    cell = np.zeros((height, width, 4), dtype=np.float32)
    cell[:, :] = color[:4] if len(color) >= 4 else (*color, 1.0)
    return cell


def unique_materials(obj: bpy.types.Object) -> list[bpy.types.Material | None]:
    found: list[bpy.types.Material | None] = []
    seen: set[int] = set()
    for slot in obj.material_slots:
        mat = slot.material
        key = id(mat) if mat is not None else 0
        if key in seen:
            continue
        seen.add(key)
        found.append(mat)
    if not found:
        raise RuntimeError("Joined mesh has no materials")
    return found


def pack_atlas(materials: list[bpy.types.Material | None]) -> tuple[np.ndarray, int]:
    count = len(materials)
    cols = max(1, ceil(sqrt(count)))
    rows = ceil(count / cols)
    cell = ATLAS_SIZE // max(cols, rows)
    inner = max(1, cell - CELL_PAD * 2)
    atlas = np.zeros((ATLAS_SIZE, ATLAS_SIZE, 4), dtype=np.float32)
    print(f"Packing {count} material(s) into a {cols}x{rows} atlas ({cell}px cells)")

    for index, mat in enumerate(materials):
        col = index % cols
        row = index // cols
        image, color = basecolor_source(mat)
        name = mat.name if mat is not None else "None"
        if image is not None:
            print(f"  [{index}] {name} <- {image.name} ({image.size[0]}x{image.size[1]})")
            tile = resize_nearest(image_pixels(image), inner, inner)
        else:
            print(f"  [{index}] {name} <- solid {tuple(round(c, 3) for c in color[:3])}")
            tile = solid_image(color, inner, inner)
        y0 = row * cell + CELL_PAD
        x0 = col * cell + CELL_PAD
        atlas[y0 : y0 + inner, x0 : x0 + inner, : tile.shape[2]] = tile
    return atlas, cols


def remap_uvs(obj: bpy.types.Object, materials: list[bpy.types.Material | None], cols: int) -> None:
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv_layer = mesh.uv_layers.active
    rows = ceil(len(materials) / cols)
    cell = ATLAS_SIZE // max(cols, rows)
    inner = max(1, cell - CELL_PAD * 2)

    mat_to_index = {id(mat): i for i, mat in enumerate(materials)}
    slot_to_index = []
    for slot in obj.material_slots:
        mat = slot.material
        slot_to_index.append(mat_to_index.get(id(mat) if mat is not None else 0, 0))

    uv = np.empty(len(uv_layer.data) * 2, dtype=np.float32)
    uv_layer.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)

    loop_start = np.empty(len(mesh.polygons), dtype=np.int32)
    loop_total = np.empty(len(mesh.polygons), dtype=np.int32)
    mat_index = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get("loop_start", loop_start)
    mesh.polygons.foreach_get("loop_total", loop_total)
    mesh.polygons.foreach_get("material_index", mat_index)

    scale = inner / ATLAS_SIZE
    for poly_i, slot_i in enumerate(mat_index):
        index = slot_to_index[slot_i] if 0 <= slot_i < len(slot_to_index) else 0
        col = index % cols
        row = index // cols
        start = int(loop_start[poly_i])
        stop = start + int(loop_total[poly_i])
        u = np.clip(uv[start:stop, 0], 0.0, 1.0)
        v = np.clip(uv[start:stop, 1], 0.0, 1.0)
        uv[start:stop, 0] = u * scale + (col * cell + CELL_PAD) / ATLAS_SIZE
        uv[start:stop, 1] = v * scale + (row * cell + CELL_PAD) / ATLAS_SIZE

    uv_layer.data.foreach_set("uv", uv.ravel())
    uv_layer.active_render = True


def save_atlas_image(pixels: np.ndarray, path: Path) -> bpy.types.Image:
    old = bpy.data.images.get("AtlasColor")
    if old is not None:
        bpy.data.images.remove(old)
    image = bpy.data.images.new("AtlasColor", width=ATLAS_SIZE, height=ATLAS_SIZE, alpha=True)
    image.colorspace_settings.name = "sRGB"
    flat = np.ascontiguousarray(pixels.reshape(-1), dtype=np.float32)
    image.pixels.foreach_set(flat)
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    return image


def make_atlas_material(image: bpy.types.Image) -> bpy.types.Material:
    mat = bpy.data.materials.get(MATERIAL_NAME)
    if mat is None:
        mat = bpy.data.materials.new(MATERIAL_NAME)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.location = (-220, 0)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.6
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 0.0
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = 1.0
    mat.blend_method = "OPAQUE"
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    return mat


def main() -> None:
    object_mode()
    meshes = source_meshes()
    if not meshes:
        raise RuntimeError("No mesh objects to combine. Select the clothing meshes and run again.")
    print(f"Combining {len(meshes)} mesh(es): " + ", ".join(o.name for o in meshes))

    out = resolve_output()
    out.parent.mkdir(parents=True, exist_ok=True)

    joined = join_copies(meshes)
    materials = unique_materials(joined)
    pixels, cols = pack_atlas(materials)
    remap_uvs(joined, materials, cols)
    image = save_atlas_image(pixels, out)
    print(f"Wrote {out} ({out.stat().st_size} bytes)")

    mat = make_atlas_material(image)
    joined.data.materials.clear()
    joined.data.materials.append(mat)
    if KEEP_ORIGINALS:
        for mesh in meshes:
            mesh.hide_set(True)
    print(f"Done. Object '{joined.name}' uses one material '{mat.name}'.")


if __name__ == "__main__":
    main()
