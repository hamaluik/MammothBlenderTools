import bpy

class MammothComponents(bpy.types.Panel):
	bl_label = 'Mammoth Components'
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'object'

	def draw(self, context):
		layout = self.layout
		obj = context.object
		
		for key, attributes in bpy.mammothComponentsLayout.items():
			comp = getattr(obj, "mammoth_component_%s" % key)
			if comp.internal___active:
				row = layout.row()
				row.label(key)
				row.operator("wm.delete_mammoth_component", text="", icon="X").component_name=key
				
				split = layout.split(percentage=0.1)
				col = split.column()
				col.label(" ")
				col = split.column()
				for attribute in attributes:
					col.prop(comp, attribute['name'])
					
				layout.separator()
		
		layout.operator("wm.call_menu", text="Add Component").name="OBJECT_MT_add_mammoth_component_menu"
		
		row = layout.row()
		row.prop(context.scene.mammoth_components_settings, "definitions_path", text="Definitions File")
		row.operator("wm.reload_mammoth_components", text="", icon="FILE_REFRESH")