import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper

# adapted from https://github.com/Kupoman/blendergltf

class MammothExporter(bpy.types.Operator, ExportHelper):
	bl_idname = "export_mammoth_scene.gltf"
	bl_label = "Export Mammoth GLTF"
	filename_ext = ".gltf"
	filter_glob = StringProperty(default="*.gltf", options={'HIDDEN'})
	check_extension = True

	# TODO: put export options as properties here
	#buffers_embed_data = BoolProperty(name='Embed Buffer Data', default=False)

	def execute(self, context):
		print("TODO: export the file!")
		return {'FINISHED'}