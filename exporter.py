import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper
import json

# adapted from https://github.com/Kupoman/blendergltf

def togl(matrix):
	return [i for col in matrix.col for i in col]

def sort_quat(quat):
	q = [i for i in quat]
	return [q[1], q[2], q[3], q[0]]

class MammothExporter(bpy.types.Operator, ExportHelper):
	bl_idname = "export_mammoth_scene.gltf"
	bl_label = "Export Mammoth GLTF"
	filename_ext = ".gltf"
	filter_glob = StringProperty(default="*.gltf", options={'HIDDEN'})
	check_extension = True

	# TODO: put export options as properties here
	pretty_print = BoolProperty(name='Pretty Print', default=True)

	def export_nodes(self, scene, objects):
		def export_node(obj):
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

			# now build the dictionary
			ob = {
				'name': obj.name,
				'children': ['node_' + child.name for child in obj.children],
				'matrix': togl(obj.matrix_world),
				'translation': [i for i in obj.location],
				'rotation': sort_quat(obj.rotation_quaternion),
				'scale': [i for i in obj.scale],
				'extensions': [{
					'mammoth': components
				}]
			}

			# TODO: things relating to type
			
			return ob

		gltf_nodes = {'node_' + obj.name: export_node(obj) for obj in objects}
		return gltf_nodes
	
	def process(self, scene):
		object_list = list(scene.get('objects', []))

		gltf = {
			'asset': {
				'version': '1.0',
				'profile': {'api': 'WebGL', 'version': '1.0.3'}
			},
			'nodes': self.export_nodes(scene, object_list)
		}
		return gltf

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

		# convert our scene into GLTF
		gltf = self.process(scene)

		# and save it to file!
		with open(self.filepath, 'w') as fout:
			indent = None
			if self.pretty_print:
				indent = 4

			json.dump(gltf, fout, indent=indent, sort_keys=True, check_circular=False)
			if self.pretty_print:
				fout.write('\n')

		return {'FINISHED'}