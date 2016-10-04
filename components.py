import bpy
from bpy.props import *
from bpy.types import PropertyGroup

layout = {}
registered = {}

def load():
    # build our component property groups
    for key, attributes in layout.items():
        name = "mammoth_component_%s" % key
        
        # build the component dictionary
        # by default, all objects will have all components
        # use this switch to denote whether the object
        # _actually_ has the component or not
        attribute_dict = {"internal___active": BoolProperty(default=False)}
        for attribute in attributes:
            # TODO: more attribute types
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
        registered[key] = compType
    print("loaded components:")
    print(layout)

def unload():
    # unregister our components
    try:
        for key, value in registered.items():
            name = "mammoth_component_%s" % key
            delattr(bpy.types.Object, name)
            bpy.utils.unregister_class(value)
    except UnboundLocalError:
        pass
    layout = {}
    registered = {}