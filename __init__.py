bl_info = {
	'name': 'Mammoth Tools',
	'description': 'Various tools for adding components to objects and exporting the result as GLTF',
	'author': 'Kenton Hamaluik',
	'version': (0, 0, 1),
	'blender': (2, 75, 0),
	'location': 'Properties > Object',
	'warning': 'Still very much under development!',
	'wiki_url': 'https://github.com/BlazingMammothGames/mammoth_blender_tools',
	'tracker_url': 'https://github.com/BlazingMammothGames/mammoth_blender_tools/issues',
	'support': 'TESTING',
	'category': 'Game Engine'
}

if "bpy" in locals():
	import imp
	imp.reload(panels)
	imp.reload(components)
	imp.reload(settings)
	print("Reloaded mammoth tools")
else:
	from . import panels
	from . import components
	from . import settings
	print("Imported mammoth tools")

import bpy
from bpy.props import *

def register():
	bpy.utils.register_class(panels.MammothComponents)
	bpy.utils.register_class(settings.MammothComponentsSettings)
	bpy.types.Scene.mammoth_components_settings = PointerProperty(type=settings.MammothComponentsSettings)
	components.load()

def unregister():
	bpy.utils.unregister_class(panels.MammothComponents)
	bpy.utils.unregister_class(settings.MammothComponentsSettings)
	del bpy.types.Scene.mammoth_components_settings
	components.unload()

if __name__ == '__main__':
	register()