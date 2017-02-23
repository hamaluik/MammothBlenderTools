import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper
import json

# adapted from https://github.com/Kupoman/blendergltf

class MammothExporter(bpy.types.Operator, ExportHelper):
	bl_idname = "export_mammoth_scene.json"
	bl_label = "Export Mammoth"
	filename_ext = ".json"
	filter_glob = StringProperty(default="*.json", options={'HIDDEN'})
	check_extension = True

	# TODO: put export options as properties here
	pretty_print = BoolProperty(name='Pretty Print', default=True)

	def execute(self, context):
		# collect all the scene data
		scene = {
			'actions': list(bpy.data.actions),
			'cameras': list(bpy.data.cameras),
			'lamps': list(bpy.data.lamps),
			'images': list(bpy.data.images),
			'materials': list(bpy.data.materials),
			'meshes': list(bpy.data.meshes),
			'objects': list(bpy.data.objects),
			'scenes': list(bpy.data.scenes),
			'textures': list(bpy.data.textures),
		}

		# convert our scene into JSON
		data = self.process(scene)

		# and save it to file!
		with open(self.filepath, 'w') as fout:
			indent = None
			if self.pretty_print:
				indent = 4

			json.dump(data, fout, indent=indent, sort_keys=True, check_circular=False)
			if self.pretty_print:
				fout.write('\n')

		return {'FINISHED'}
	
	def process(self, scene):
		data = {
			'meta': {
				'file': bpy.path.clean_name(bpy.path.basename(bpy.data.filepath)),
				'blender': bpy.app.version_string,
				'version': '0.0.0',
			},
			'objects': self.export_objects(scene),
			'meshes': self.export_meshes(scene),
			'lights': self.export_lights(scene),
			'cameras': self.export_cameras(scene),
			'materials': self.export_materials(scene)
		}
		return data

	def export_objects(self, scene):
		objects = list(scene.get('objects', []))
		def export_object(obj):
			# first get our attached components
			components = {}
			for key, attributes in bpy.mammothComponentsLayout.items():
				comp = getattr(obj, "mammoth_component_%s" % key)
				if comp.internal___active:
					components[key] = {}
					for attribute in attributes:
						# TODO: more attribute types
						if attribute['type'] == 'int' or \
						   attribute['type'] == 'float' or \
						   attribute['type'] == 'bool' or \
						   attribute['type'] == 'string':
							components[key][attribute['name']] = getattr(comp, attribute['name'])
						elif attribute['type'] == 'ivec2' or \
							 attribute['type'] == 'ivec3' or \
							 attribute['type'] == 'ivec4' or \
							 attribute['type'] == 'vec2' or \
							 attribute['type'] == 'vec3' or \
							 attribute['type'] == 'vec4' or \
							 attribute['type'] == 'colour':
							components[key][attribute['name']] = [i for i in getattr(comp, attribute['name'])]
						else:
							raise TypeError('Unsupported Mammoth attribute type \'%s\' for %s on %s' % (attribute['type'], attribute['name'], key))

			def sort_quat(quat):
				q = [i for i in quat]
				return [q[1], q[2], q[3], q[0]]

			# now build the dictionary
			ob = {
				'children': {child.name: export_object(child) for child in obj.children},
				'translation': [i for i in obj.location],
				'rotation': sort_quat(obj.rotation_quaternion),
				'scale': [i for i in obj.scale],
				'components': components
			}
			
			return ob

		# export each _root_ object (only objects without parents)
		object_array = {obj.name: export_object(obj) for obj in objects if obj.parent is None}
		return object_array

	def export_meshes(self, scene):
		# TODO
		return []

	def export_lights(self, scene):
		# TODO
		return []

	def export_cameras(self, scene):
		# TODO
		return []

	def export_materials(self, scene):
		# TODO
		return []