import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper
import json
import base64
import struct
import bmesh
import zlib

# adapted from https://github.com/Kupoman/blendergltf

# helper class for dealing with vertices
#class Vertex:
#    __slots__ = ['position', 'normal', 'uvs', 'colours', 'index', 'loop_indices']
#
#    def __init__(self, mesh, loop):
#        self.position     = mesh.vertices[loop.vertex_index].co
#        self.normal       = mesh.vertices[loop.vertex_index].normal
#        self.uvs          = tuple(layer.data[loop.index].uv for layer in mesh.uv_layers)
#        self.colours      = tuple(layer.data[loop.index].color for layer in mesh.vertex_colors)
#        self.index        = loop.vertex_index
#        self.loop_indices = [loop.index]
class Vertex:
    __slots__ = ['position', 'normal', 'uv', 'colour', 'index']

    def __init__(self, vertex):
        self.position = vertex.co
        self.normal = vertex.normal
        self.uv = None
        self.colour = None
        self.index = vertex.index

class MammothExporter(bpy.types.Operator, ExportHelper):
    bl_idname = "export_mammoth_scene.json"
    bl_label = "Export Mammoth"
    filename_ext = ".json"
    filter_glob = StringProperty(default="*.json", options={'HIDDEN'})
    check_extension = True

    # TODO: put export options as properties here
    pretty_print = BoolProperty(name='Pretty Print', default=True)
    pack_images = BoolProperty(name='Pack Images', default=False)

    def execute(self, context):
        # collect all the scene data
        scene = {
            'actions': list(bpy.data.actions),
            'cameras': list(bpy.data.cameras),
            'lights': list(bpy.data.lamps),
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
        #import sys
        #mod_version = sys.modules['mammoth_blender_tools'].bl_info.get('version')
        #mod_version_string = '.'.join(str(v) for v in mod_version)
        mod_version_string = '0.0.0' # TODO

        data = {
            'meta': {
                'file': bpy.path.clean_name(bpy.path.basename(bpy.data.filepath)),
                'blender': bpy.app.version_string,
                'exporter_version': mod_version_string,
            },
            'objects': self.export_objects(scene),
            'meshes': self.export_meshes(scene),
            'lights': self.export_lights(scene),
            'cameras': self.export_cameras(scene),
            'shaders': self.export_materials(scene),
            'textures': self.export_textures(scene),
            'images': self.export_images(scene)
        }
        return data

    def export_objects(self, scene):
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
            node = {
                'name': obj.name
            }

            if obj.mammoth_use_transform:
                oldMode = obj.rotation_mode
                obj.rotation_mode = 'QUATERNION'
                node['transform'] = {
                    'translation': [i for i in obj.location],
                    'rotation': sort_quat(obj.rotation_quaternion),
                    'scale': [i for i in obj.scale]
                }
                obj.rotation_mode = oldMode

            if obj.children is not None and len(obj.children) > 0:
                node['children'] = [export_object(child) for child in obj.children]

            if components is not None and len(components) > 0:
                node['components'] = components

            if obj.type == 'MESH':
                node['render'] = { 'mesh': obj.data.name }
                if len(obj.material_slots) > 0 and obj.material_slots[0].material is not None:
                    node['render']['shader'] = obj.material_slots[0].material.name
            elif obj.type == 'EMPTY':
                pass
            elif obj.type == 'CAMERA':
                node['camera'] = obj.data.name
            elif obj.type == 'LAMP':
                node['light'] = obj.data.name
            else:
                raise TypeError('Unsupported object type \'%s\' (%s)' % (obj.type, obj.name))
            
            return node

        # export each _root_ object (only objects without parents)
        objects = list(scene.get('objects', []))
        return [export_object(obj) for obj in objects if obj.parent is None]

    def export_meshes(self, scene):
        def export_mesh(src_mesh):
            me = {
                'name': src_mesh.name
            }

            # triangulate the mesh
            bm = bmesh.new()
            bm.from_mesh(src_mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method=0, ngon_method=0)
            mesh = bpy.data.meshes.new(src_mesh.name)
            bm.to_mesh(mesh)
            bm.free()

            # prep the mesh for export
            mesh.calc_normals_split()
            mesh.calc_tessface()

            # how many bytes per vertex?
            # position + normal + uv + colours
            vertexSize = (3 + 3 + (len(mesh.uv_layers) * 2) + (len(mesh.vertex_colors) * 3)) * 4

            # extract the vertices
            #vertices = [Vertex(mesh, loop) for loop in mesh.loops]
            vertices = [Vertex(vertex) for vertex in mesh.vertices]

            # add UV data
            if len(mesh.uv_layers) > 0:
                for loop in mesh.loops:
                    vertices[loop.vertex_index].uv = mesh.uv_layers[0].data[loop.index].uv

            # add colour data
            if len(mesh.vertex_colors) > 0:
                for loop in mesh.loops:
                    vertices[loop.vertex_index].colour = mesh.vertex_colors[0].data[loop.index].color

            vData = bytearray(vertexSize * len(vertices))
            i = 0
            for vertex in vertices:
                struct.pack_into('ffffff', vData, i,
                    vertex.position[0], vertex.position[1], vertex.position[2],
                    vertex.normal[0], vertex.normal[1], vertex.normal[2]
                )
                i += struct.calcsize('ffffff')

                if vertex.uv is not None:
                    struct.pack_into('ff', vData, i, vertex.uv[0], vertex.uv[1])
                    i += struct.calcsize('ff')

                if vertex.colour is not None:
                    struct.pack_into('fff', vData, i, vertex.colour[0], vertex.colour[1], vertex.colour[2])
                    i += struct.calcsize('fff')

            # base-64 encode them
            me['vertices'] = 'data:text/plain;base64,' + base64.b64encode(vData).decode('ascii')
            self.report({'INFO'}, '[Mammoth] Encoded %d vertices into %d bytes (%d base-64)' % (len(vertices), len(vData), len(me['vertices'])))
            #self.report({'INFO'}, '; '.join(', '.join(str(p) for p in e.position) for e in vertices))

            # record how the vertices are laid out
            vertexDescription = ['position', 'normal']
            if len(mesh.uv_layers) > 0:
                vertexDescription.append('uv')
            if len(mesh.vertex_colors) > 0:
                vertexDescription.append('colour')
            me['vlayout'] = vertexDescription

            # add the indices
            triangles = [face.vertices for face in mesh.polygons]
            i = 0
            iData = bytearray(struct.calcsize('iii') * len(triangles))
            for triangle in triangles:
                struct.pack_into('iii', iData, i, triangle[0], triangle[1], triangle[2])
                i += struct.calcsize('iii')

            # base-64 encode the indices
            me['indices'] = 'data:text/plain;base64,' + base64.b64encode(iData).decode('ascii')
            self.report({'INFO'}, '[Mammoth] Encoded %d vertex indices into %d bytes (%d base-64)' % (len(triangles) * 3, len(iData), len(me['indices'])))
            #self.report({'INFO'}, '; '.join(', '.join(str(i) for i in t) for t in triangles))

            # destroy our temporary mesh
            bpy.data.meshes.remove(mesh, do_unlink=True)

            return me

        meshes = list(scene.get('meshes', []))
        return [export_mesh(mesh) for mesh in meshes]

    def export_lights(self, scene):
        def export_light(light):
            lit = {
                'name': light.name,
                'colour': (light.color * light.energy)[:]
            }

            if light.type == 'SUN':
                lit['type'] = 'directional'
            elif light.type == 'POINT':
                lit['type'] = 'point'
                lit['distance'] = light.distance
            else:
                raise TypeError('Unsupported light type \'%s\' (%s)' % (light.type, light.name))

            return lit

        lights = list(scene.get('lights'))
        return [export_light(light) for light in lights]

    def export_cameras(self, scene):
        def export_camera(camera):
            scene0 = list(scene.get('scenes', []))[0]

            cam = {
                'name': camera.name,
                'near': camera.clip_start,
                'far':  camera.clip_end,
                'clearColour': list(scene0.world.horizon_color[:])
            }

            if camera.type == 'ORTHO':
                cam['type'] = 'orthographic'
                cam['ortho_size'] = camera.ortho_scale
            elif camera.type == 'PERSP':
                cam['type'] = 'perspective'
                cam['fov'] = camera.angle_y
                cam['aspect'] = camera.angle_x / camera.angle_y
            else:
                raise TypeError('Unsupported camera type \'%s\' (%s)' % (camera.type, camera.name))

            return cam

        cameras = list(scene.get('cameras', []))
        return [export_camera(cam) for cam in cameras]

    def export_materials(self, scene):
        scene0 = list(scene.get('scenes', []))[0]

        def export_material(material):
            mat = {
                'name': material.name,
                'textures': []
            }

            if material.use_shadeless:
                mat['unlit'] = {
                    'colour': list((material.diffuse_color * material.diffuse_intensity)[:]) + [material.alpha]
                }
            elif material.specular_intensity == 0.0:
                mat['diffuse'] = {
                    'ambient': list((scene0.world.ambient_color * material.ambient)[:]) + [1.0],
                    'colour': list((material.diffuse_color * material.diffuse_intensity)[:]) + [material.alpha]
                }
            else:
                raise TypeError('Unsupported material (%s), should be either unlit or have 0 specular intensity!' % material.name)

            textures = [texture for texture in material.texture_slots if texture and texture.texture.type == 'IMAGE']
            diffuseTextures = [t.texture.name for t in textures if t.use_map_color_diffuse]
            if diffuseTextures and len(diffuseTextures) > 0:
                #mat['textures']['diffuse'] = diffuseTextures
                mat['textures'].extend(diffuseTextures)

            return mat

        materials = list(scene.get('materials', []))
        return [export_material(material) for material in materials]

    def export_textures(self, scene):
        def export_texture(texture):
            tex = {
                'name': texture.name,
                'type': texture.type.lower()
            }

            if type(texture) is bpy.types.ImageTexture:
                tex['image'] = {
                    'name': texture.image.name,
                    'wrap': 'repeat' if texture.extension == 'REPEAT' else 'clamp',
                    'filter': 'bilinear' if texture.use_interpolation else 'point'
                }

            return tex
        textures = list(scene.get('textures', []))
        return [export_texture(texture) for texture in textures]

    def export_images(self, scene):
        def image_to_png_uri(image, asBytes=False):
            width = image.size[0]
            height = image.size[1]
            buf = bytearray([int(p * 255) for p in image.pixels])

            # reverse the vertical line order and add null bytes at the start
            width_byte_4 = width * 4
            raw_data = b''.join(b'\x00' + buf[span:span + width_byte_4] for span in range((height - 1) * width_byte_4, -1, - width_byte_4))

            def png_pack(png_tag, data):
                chunk_head = png_tag + data
                return (struct.pack("!I", len(data)) +
                        chunk_head +
                        struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head)))

            png_bytes = b''.join([
                b'\x89PNG\r\n\x1a\n',
                png_pack(b'IHDR', struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0)),
                png_pack(b'IDAT', zlib.compress(raw_data, 9)),
                png_pack(b'IEND', b'')])

            if asBytes:
                return png_bytes
            else:
                return 'data:image/png;base64,' + base64.b64encode(png_bytes).decode('ascii')

        def export_image(image):
            im = {
                'name': image.name,
                'width': image.size[0],
                'height': image.size[1]
            }

            if self.pack_images or image.packed_file is not None:
                im['uri'] = image_to_png_uri(image)
            else:
                im['uri'] = image.filepath.replace('\\', '/')

            return im
        images = list(scene.get('images', []))
        return [export_image(image) for image in images]