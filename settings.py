import bpy
from bpy.props import *
from bpy.types import PropertyGroup

from . import components

class MammothComponents(PropertyGroup):
	def definitions_path_updated(self, context):
		components.unload()
		import os
		if os.path.splitext(self.definitions_path)[1] == '.json':
			with open(bpy.path.abspath(self.definitions_path)) as definition_file:
				import json
				bpy.mammothComponentsLayout = json.load(definition_file)
		else:
			print('Definitions must be .json files!')
		print(bpy.mammothComponentsLayout)
		components.load()
		
	definitions_path = StringProperty(
		name="definitions_path",
		description="Path to the component descriptions file",
		default="*.json",
		options={'HIDDEN'},
		maxlen=1024,
		subtype='FILE_PATH',
		update=definitions_path_updated
	)