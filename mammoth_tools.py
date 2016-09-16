import bpy
from bpy.props import BoolProperty, StringProperty, FloatProperty, IntProperty, FloatVectorProperty, PointerProperty
from bpy.types import PropertyGroup

bpy.mammothComponentsLayout = {}
bpy.mammothRegisteredComponents = {}

def loadComponents():
    # build our component property groups
    for key, attributes in bpy.mammothComponentsLayout.items():
        name = "mammoth_component_%s" % key
        
        # build the component dictionary
        # by default, all objects will have all components
        # use this switch to denote whether the object
        # _actually_ has the component or not
        attribute_dict = {"internal___active": BoolProperty(default=False)}
        for attribute in attributes:
            
            if attribute['type'] == 'float':
                attribute_dict[attribute['name']] = FloatProperty(name=attribute['name'])
            elif attribute['type'] == 'string':
                attribute_dict[attribute['name']] = StringProperty(name=attribute['name'])
            else:
                raise TypeError('Unsupported Mammoth attribute type \'%s\' for %s on %s' % (attribute['type'], attribute['name'], key))
        
        # build the component type
        compType = type(name, (PropertyGroup,), attribute_dict)
        
        # register it with blender (and python)
        bpy.utils.register_class(compType)
        setattr(bpy.types.Object, name, PointerProperty(type=compType))
        
        # store it for later
        bpy.mammothRegisteredComponents[key] = compType

def unloadComponents():
    # unregister our components
    try:
        for key, value in bpy.mammothRegisteredComponents.items():
            name = "mammoth_component_%s" % key
            delattr(bpy.types.Object, name)
            bpy.utils.unregister_class(value)
    except UnboundLocalError:
        pass
    bpy.mammothComponentsLayout = {}
    bpy.mammothRegisteredComponents = {}

class MammothComponentsSettings(PropertyGroup):
    def definitions_path_updated(self, context):
        unloadComponents()
        # TODO: load components from the JSON file
        import os
        if os.path.splitext(self.definitions_path)[1] == '.json':
            with open(bpy.path.abspath(self.definitions_path)) as definition_file:
                import json
                bpy.mammothComponentsLayout = json.load(definition_file)
        else:
            print('Definitions must be .json files!')
        print(bpy.mammothComponentsLayout)
        loadComponents()
        
    definitions_path = StringProperty(
        name="definitions_path",
        description="Path to the component descriptions file",
        default="*.json",
        options={'HIDDEN'},
        maxlen=1024,
        subtype='FILE_PATH',
        update=definitions_path_updated
    )

class MammothComponentsPanel(bpy.types.Panel):
    bl_label = "Mammoth Components"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

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

class AddMammothComponentOperator(bpy.types.Operator):
    bl_idname = "wm.add_mammoth_component"
    bl_label = "Add Mammoth Component"
    
    component_name = StringProperty(name="component_name")
    
    def execute(self, context):
        obj = context.object
        comp = getattr(obj, "mammoth_component_%s" % self.component_name)
        comp.internal___active = True
        context.area.tag_redraw()
        return {'FINISHED'}
    
class DeleteMammothComponentOperator(bpy.types.Operator):
    bl_idname = "wm.delete_mammoth_component"
    bl_label = "Delete Mammoth Component"
    
    component_name = StringProperty(name="component_name")
    
    def execute(self, context):
        obj = context.object
        comp = getattr(obj, "mammoth_component_%s" % self.component_name)
        comp.internal___active = False
        context.area.tag_redraw()
        return {'FINISHED'}

class AddMammothComponentMenu(bpy.types.Menu):
    bl_label = "Add Mammoth Component"
    bl_idname = "OBJECT_MT_add_mammoth_component_menu"

    def draw(self, context):
        layout = self.layout

        for key in bpy.mammothComponentsLayout.keys():
            layout.operator("wm.add_mammoth_component", text=key).component_name=key

def register():
    bpy.utils.register_class(MammothComponentsSettings)
    bpy.utils.register_class(MammothComponentsPanel)
    bpy.utils.register_class(AddMammothComponentMenu)
    bpy.utils.register_class(AddMammothComponentOperator)
    bpy.utils.register_class(DeleteMammothComponentOperator)
    bpy.types.Scene.mammoth_components_settings = PointerProperty(type=MammothComponentsSettings)
    loadComponents()

def unregister():
    bpy.utils.unregister_class(MammothComponentsSettings)
    bpy.utils.unregister_class(MammothComponentsPanel)
    bpy.utils.unregister_class(AddMammothComponentMenu)
    bpy.utils.unregister_class(AddMammothComponentOperator)
    bpy.utils.unregister_class(DeleteMammothComponentOperator)
    del bpy.types.Scene.mammoth_components_settings
    unloadComponents()

if __name__ == "__main__":
    register()
