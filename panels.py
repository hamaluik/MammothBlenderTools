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
				col = layout.column()
				row = col.row()
				row.label(key)
				row.operator("wm.delete_mammoth_component", text="", icon="X").component_name=key
				
				row = col.row()
				for attribute in attributes:
					col.prop(comp, attribute['name'])
					
				layout.separator()
		
		layout.operator("wm.call_menu", text="Add Component").name="OBJECT_MT_add_mammoth_component_menu"
		layout.prop(context.scene.mammoth_components_settings, "definitions_path", text="Definitions File")