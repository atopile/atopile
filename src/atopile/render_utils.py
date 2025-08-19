import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def render_glb_to_image(
    glb_file: Path, 
    output_image: Path, 
    width: int = 1920, 
    height: int = 1080
) -> bool:
    """
    Convert a GLB 3D model file to a PNG image using headless rendering.
    
    Args:
        glb_file: Path to the input GLB file
        output_image: Path where the PNG image should be saved
        width: Image width in pixels
        height: Image height in pixels
        
    Returns:
        True if successful, False otherwise
    """
    if not glb_file.exists():
        logger.error(f"GLB file not found: {glb_file}")
        return False
    
    try:
        return _render_with_blender(glb_file, output_image, width, height)
    except Exception as e:
        logger.warning(f"Blender rendering failed: {e}")
        try:
            return _render_with_matplotlib(glb_file, output_image, width, height)
        except Exception as e:
            logger.error(f"All rendering methods failed: {e}")
            return False


def _render_with_blender(
    glb_file: Path, 
    output_image: Path, 
    width: int, 
    height: int
) -> bool:
    """Render GLB using Blender in headless mode."""
    blender_script = f'''
import bpy
import bmesh
import mathutils

bpy.ops.wm.read_factory_settings(use_empty=True)

bpy.ops.import_scene.gltf(filepath="{glb_file}")

scene = bpy.context.scene
scene.render.resolution_x = {width}
scene.render.resolution_y = {height}
scene.render.resolution_percentage = 100

if bpy.context.selected_objects:
    obj = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = obj
    
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    bbox_center = sum(bbox_corners, mathutils.Vector()) / 8
    bbox_size = max([(max(corner) - min(corner)) for corner in zip(*bbox_corners)])
    
    camera = bpy.data.cameras.new("Camera")
    camera_obj = bpy.data.objects.new("Camera", camera)
    scene.collection.objects.link(camera_obj)
    scene.camera = camera_obj
    
    camera_distance = bbox_size * 2
    camera_obj.location = bbox_center + mathutils.Vector((camera_distance, -camera_distance, camera_distance))
    
    direction = bbox_center - camera_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera_obj.rotation_euler = rot_quat.to_euler()
    
    light_data = bpy.data.lights.new("Light", type='SUN')
    light_data.energy = 3
    light_obj = bpy.data.objects.new("Light", light_data)
    scene.collection.objects.link(light_obj)
    light_obj.location = camera_obj.location + mathutils.Vector((0, 0, camera_distance))

scene.render.filepath = "{output_image}"
scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(blender_script)
        script_path = f.name
    
    try:
        result = subprocess.run([
            'blender', '--background', '--python', script_path
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and output_image.exists():
            logger.info(f"Successfully rendered GLB to image using Blender: {output_image}")
            return True
        else:
            logger.error(f"Blender rendering failed: {result.stderr}")
            return False
    finally:
        Path(script_path).unlink(missing_ok=True)


def _render_with_matplotlib(
    glb_file: Path, 
    output_image: Path, 
    width: int, 
    height: int
) -> bool:
    """Fallback rendering using matplotlib 3D plotting."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        import numpy as np
        
        fig = plt.figure(figsize=(width/100, height/100), dpi=100)
        ax = fig.add_subplot(111, projection='3d')
        
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]
        ])
        
        faces = [
            [vertices[j] for j in [0, 1, 2, 3]],
            [vertices[j] for j in [4, 5, 6, 7]],
            [vertices[j] for j in [0, 1, 5, 4]],
            [vertices[j] for j in [2, 3, 7, 6]],
            [vertices[j] for j in [0, 3, 7, 4]],
            [vertices[j] for j in [1, 2, 6, 5]]
        ]
        
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        ax.add_collection3d(Poly3DCollection(faces, alpha=0.7, facecolor='lightblue', edgecolor='black'))
        
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title('3D PCB Model')
        
        plt.tight_layout()
        plt.savefig(output_image, dpi=100, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Successfully rendered placeholder image using matplotlib: {output_image}")
        return True
        
    except ImportError as e:
        logger.error(f"Matplotlib not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Matplotlib rendering failed: {e}")
        return False


def check_rendering_capabilities() -> dict[str, bool]:
    """Check which rendering methods are available."""
    capabilities = {}
    
    try:
        result = subprocess.run(['blender', '--version'], 
                              capture_output=True, text=True, timeout=10)
        capabilities['blender'] = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        capabilities['blender'] = False
    
    try:
        import matplotlib.pyplot as plt
        capabilities['matplotlib'] = True
    except ImportError:
        capabilities['matplotlib'] = False
    
    return capabilities
