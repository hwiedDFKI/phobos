#!/usr/bin/python
# coding=utf-8

"""
Copyright 2014, University of Bremen & DFKI GmbH Robotics Innovation Center

This file is part of Phobos, a Blender Add-On to edit robot models.

Phobos is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License
as published by the Free Software Foundation, either version 3
of the License, or (at your option) any later version.

Phobos is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with Phobos.  If not, see <http://www.gnu.org/licenses/>.

File phobosgui.py

Created on 6 Jan 2014

@author: Kai von Szadkowski
"""

import sys
import inspect

import bpy
# import bgl
from bpy.props import (BoolProperty, IntProperty, StringProperty, EnumProperty,
                       PointerProperty, CollectionProperty)
from bpy.types import AddonPreferences

from . import defs
from phobos.phoboslog import loglevels
from phobos.io import entities
from phobos.io import meshes
from phobos.io import scenes
from phobos.io import libraries


class ModelPoseProp(bpy.types.PropertyGroup):
    robot_name = StringProperty()
    label = StringProperty()
    hide = BoolProperty(default=True)
    parent = StringProperty()
    icon = StringProperty()
    type = StringProperty()
    path = StringProperty()
    model_file = StringProperty()
    preview = StringProperty()


class PhobosPrefs(AddonPreferences):
    bl_idname = __package__

    logfile = StringProperty(
        name="logfile",
        subtype="FILE_PATH",
        default="."
    )

    loglevel = EnumProperty(
        name="loglevel",
        items=tuple(((l,) * 3 for l in loglevels)),
        default="ERROR"
    )

    logtofile = BoolProperty(
        name="logtofile",
        default=False
    )

    logtoterminal = BoolProperty(
        name="logtoterminal",
        default=True
    )

    modelsfolder = StringProperty(
        name="modelsfolder",
        subtype="DIR_PATH",
        default='',
    )

    exportpluginsfolder = StringProperty(
        name='exportpluginsfolder',
        subtype='DIR_PATH',
        default='.'
    )

    models_poses = CollectionProperty(type=ModelPoseProp)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Log Settings")
        layout.prop(self, "logfile", text="log file path")
        layout.prop(self, "logtofile", text="write to logfile")
        layout.prop(self, "logtoterminal", text="only display in terminal")
        layout.prop(self, "loglevel", text="log level")
        layout.separator()
        layout.label(text="Folders")
        layout.prop(self, "modelsfolder", text="models folder")
        # layout.prop(self, 'pluginspath', text="Path for plugins")


class PhobosExportSettings(bpy.types.PropertyGroup):

    def updateExportPath(self, context):
        if not bpy.data.worlds[0].phobosexportsettings.path.endswith('/'):
            bpy.data.worlds[0].phobosexportsettings.path += '/'

    def getMeshTypeListForEnumProp(self, context):
        return sorted([(mt,) * 3 for mt in meshes.mesh_types])

    path = StringProperty(name='path', subtype='DIR_PATH', default='../',
                          update=updateExportPath)
    # TODO is not visible in GUI?!
    structureExport = BoolProperty(name="Structure export", default=True,
                                   description="Create structured subfolders")
    selectedOnly = BoolProperty(name="Selected only", default=True,
                                description="Export only selected objects")
    decimalPlaces = IntProperty(name="decimals", description="Number of " +
                                "decimal places to export", default=5)
    exportTextures = BoolProperty(name='Export textures', default=True)
    outputMeshtype = EnumProperty(items=getMeshTypeListForEnumProp,
                                  name='link',
                                  description="Mesh type to use in exported " +
                                  "entity/scene files.")


class Mesh_Export_UIList(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        # assert(isinstance(item, bpy.types.MaterialTextureSlot)
        ma = data
        slot = item
        tex = slot.texture if slot else None
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if tex:
                layout.prop(tex, "name", text="",
                            emboss=False, icon_value=icon)
            else:
                layout.label(text="", icon_value=icon)
            if tex and isinstance(item, bpy.types.MaterialTextureSlot):
                layout.prop(ma, "use_textures", text="", index=index)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)


class Models_Poses_UIList(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        self.use_filter_show = False
        im = item
        modelsPosesColl = bpy.context.user_preferences.addons[
            "phobos"].preferences.models_poses
        if im.name in modelsPosesColl.keys():
            coll_item = modelsPosesColl[im.name]
            if coll_item.type == "robot_name":
                layout.label(text=coll_item.label,
                             translate=False, icon=coll_item.icon)
            else:
                sLayout = layout.split(0.1)
                sLayout.label(text="")
                if im.filepath != '':
                    sLayout.label(text=coll_item.label,
                                  translate=False, icon_value=icon)
                else:
                    sLayout.label(text=coll_item.label,
                                  translate=False, icon=coll_item.icon)

    def filter_items(self, context, data, propname):
        images = getattr(data, propname)
        flt_flags = [self.bitflag_filter_item] * len(images)

        modelsPosesColl = bpy.context.user_preferences.addons[
            "phobos"].preferences.models_poses

        # Filter items. Only show robots. Hide all other images
        for idx, im in enumerate(images):
            if im.name in modelsPosesColl.keys():
                curr_model = modelsPosesColl[im.name]
                if curr_model.hide and not (curr_model.type == "robot_name"):
                    flt_flags[idx] &= ~self.bitflag_filter_item
            else:
                flt_flags[idx] &= ~self.bitflag_filter_item

        # TODO remove this (never used)
        helper_funcs = bpy.types.UI_UL_list
        # Reorder by name
        flt_neworder = []
        noPreviewIndex = 0
        for im in images:
            newIndex = 0
            if im.name in modelsPosesColl.keys():
                newIndex = modelsPosesColl.keys().index(im.name)
            else:
                newIndex = len(modelsPosesColl) + noPreviewIndex
                noPreviewIndex += 1
            flt_neworder.append(newIndex)

        return flt_flags, flt_neworder


def showPreview(self, value):
    bpy.ops.scene.change_preview()


class PhobosToolsPanel(bpy.types.Panel):
    """A Custom Panel in the Phobos viewport toolbar"""
    bl_idname = "TOOLS_PT_PHOBOS_TOOLS"
    bl_label = "General Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Phobos'
    # bl_context = ''

    def draw(self, context):
        layout = self.layout

        # Tools & Selection Menu
        # layout.separator()
        tsinlayout = layout.split()
        tsc1 = tsinlayout.column(align=True)
        tsc1.label(text="Select...", icon='HAND')
        tsc1.operator('phobos.select_root', text='Root')
        tsc1.operator('phobos.select_model', text='Robot')
        tsc1.operator('phobos.select_objects_by_phobostype',
                      text="by Phobostype")
        tsc1.operator('phobos.select_objects_by_name', text="by Name")
        tsc2 = tsinlayout.column(align=True)
        tsc2.label(text="Tools", icon='MODIFIER')
        tsc2.operator('phobos.sort_objects_to_layers', icon='IMGDISPLAY')
        tsc2.operator('phobos.set_xray')
        tsc2.operator('phobos.toggle_namespaces')
        tsc2.operator('phobos.measure_distance')
        tsc2.operator('phobos.validate')


class PhobosModelPanel(bpy.types.Panel):
    """A Custom Panel in the Phobos viewport toolbar"""
    bl_idname = "TOOLS_PT_PHOBOS_MODEL"
    bl_label = "Model Editing"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Phobos'
    # bl_context = ''

    def draw_header(self, context):
        self.layout.label(icon='OUTLINER_DATA_ARMATURE')

    def draw(self, context):
        layout = self.layout

        # Robot Model Menu
        inlayout = layout.split()
        rc1 = inlayout.column(align=True)
        rc2 = inlayout.column(align=True)
        rc1.operator('phobos.name_model')
        rc2.operator('phobos.set_version')

        inlayout = layout.split()
        c1 = inlayout.column(align=True)
        c2 = inlayout.column(align=True)
        c1.operator('phobos.set_phobostype')
        c1.operator('phobos.batch_rename')
        c1.operator('phobos.edityamldictionary', icon='TEXT')
        c2.operator('phobos.batch_property', icon='GREASEPENCIL')
        c2.operator('phobos.copy_props', icon='GHOST')
        c2.operator('phobos.rename_custom_property', icon='SYNTAX_OFF')

        layout.separator()
        kinlayout = layout.split()
        kc1 = kinlayout.column(align=True)
        kc2 = kinlayout.column(align=True)
        kc1.label(text='Kinematics', icon='POSE_DATA')
        kc1.operator("phobos.create_links")
        kc1.operator('phobos.define_joint_constraints')
        kc1.operator('phobos.create_inertial_objects')
        kc1.operator("phobos.create_mimic_joint")
        kc1.operator('phobos.add_kinematic_chain', icon='CONSTRAINT')
        kc2.label(text='Visual/Collision', icon='GROUP')
        kc2.operator('phobos.create_collision_objects')
        kc2.operator('phobos.define_geometry')
        kc2.operator('phobos.set_collision_group')
        kc2.operator('phobos.smoothen_surface')

        # Masses, Inertia & Hardware
        layout.separator()
        minlayout = layout.split()
        hw1 = minlayout.column(align=True)
        hw1.label(text="Hardware", icon='MOD_SCREW')
        hw1.operator('phobos.add_motor')
        mc1 = minlayout.column(align=True)
        mc1.label(text="Masses & Inertia", icon='PHYSICS')
        mc1.operator('phobos.calculate_mass')
        mc1.operator('phobos.set_mass')
        mc1.operator('phobos.sync_masses')
        mc1.operator('phobos.edit_inertia')


# class PhobosScenePanel(bpy.types.Panel):
#     """A Custom Panel in the Phobos viewport toolbar"""
#     bl_idname = "TOOLS_PT_PHOBOS_SCENE"
#     bl_label = "Scene Editing"
#     bl_space_type = 'VIEW_3D'
#     bl_region_type = 'TOOLS'
#     bl_category = 'Phobos'
#
#     def draw_header(self, context):
#         self.layout.label(icon='SCENE_DATA')
#
#     def draw(self, context):
#         layout = self.layout
#         layout.label(text="Scene Editing", icon="WORLD")
#         iinlayout = layout.split()
#         ic1 = iinlayout.column(align=True)
#         ic1.operator("phobos.add_heightmap")
#         ic2 = iinlayout.column(align=True)
#         ic2.operator('phobos.define_entity')
#
#         layout.label(text="Robotmodels and Poses", icon="MOD_ARMATURE")
#         #layout.operator("scene.load_backed_models_operator", text="Load Models", icon="LIBRARY_DATA_DIRECT")
#         #layout.operator("scene.reload_models_and_poses_operator", text="Reload Models and Poses", icon="LIBRARY_DATA_DIRECT")
#
#
#         modelsPosesColl = bpy.context.user_preferences.addons["phobos"].preferences.models_poses
#         for model_pose in modelsPosesColl:
#             if not model_pose.name in bpy.data.images.keys():
#                 if model_pose.type == 'robot_name':
#                     bpy.data.images.new(model_pose.name,0,0)
#                 elif 'robot_pose':
#                     if model_pose.preview != '':
#                         if os.path.split(model_pose.preview)[-1] in bpy.data.images.keys():
#                             bpy.data.images[os.path.split(model_pose.preview)[-1]].reload()
#                         im = bpy.data.images.load(model_pose.preview)
#                         model_pose.name  = im.name
#                         #im.name = model_pose.name
#                         im.gl_load(0, bgl.GL_LINEAR, bgl.GL_LINEAR)
#                     else:
#                         print(model_pose.name)
#                         bpy.data.images.new(model_pose.name, 0, 0)
#
#         layout.template_list("Models_Poses_UIList", "",  bpy.data, "images", context.scene, "active_ModelPose")
#
# #        layout.template_preview(bpy.data.textures[context.scene.active_bakeModel])
# #        layout.template_preview(preview_mat.active_texture,
# #                                parent=preview_mat,
# #                                slot=preview_mat.texture_slots[preview_mat.active_texture_index],
# #                                preview_id="phobos_model_preview")
#
#         layout.operator('scene.phobos_import_selected_lib_robot', text="Import Selected Robot Bake", icon="IMPORT")
#         pinlayout = layout.split()
#         pc1 = pinlayout.column(align=True)
#         pc1.operator('phobos.store_pose2', text='Store Current Pose')
#         pc2 = pinlayout.column(align=True)
#         pc2.operator('phobos.load_pose2', text='Load Selected Pose')
#
#         layout.operator("phobos.export_current_poses", text="Export Selected Pose", icon="OUTLINER_OB_ARMATURE")
#         layout.operator("phobos.export_all_poses", text="Export All Poses", icon="OUTLINER_OB_ARMATURE")


class PhobosExportPanel(bpy.types.Panel):
    """A Custom Panel in the Phobos viewport toolbar"""
    bl_idname = "TOOLS_EXPORT_PT_PHOBOS"
    bl_label = "Export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Phobos'

    def draw_header(self, context):
        self.layout.label(icon='EXPORT')

    def draw(self, context):
        expsets = bpy.data.worlds[0].phobosexportsettings
        layout = self.layout

        # export robot model options
        layout.prop(expsets, "path")
        ginlayout = self.layout.split()
        g1 = ginlayout.column(align=True)
        # g1.prop(expsets, "relativePaths")
        # g1.prop(expsets, "structureExport")
        g1.prop(expsets, "exportTextures")
        g1.prop(expsets, "selectedOnly")
        g2 = ginlayout.column(align=True)
        g2.prop(expsets, "decimalPlaces")

        layout.separator()

        # Settings for mesh and entity export
        inlayout = self.layout.split()

        cmodel = inlayout.column(align=True)
        cmodel.label(text="Models")
        for entitytype in sorted(entities.entity_types):
            if ('export' in entities.entity_types[entitytype] and
                    'extensions' in entities.entity_types[entitytype]):
                typename = "export_entity_" + entitytype
                cmodel.prop(bpy.data.worlds[0], typename)

        cmesh = inlayout.column(align=True)
        cmesh.label(text="Meshes")
        for meshtype in sorted(meshes.mesh_types):
            if 'export' in meshes.mesh_types[meshtype]:
                typename = "export_mesh_" + meshtype
                cmesh.prop(bpy.data.worlds[0], typename)
        cmesh.prop(bpy.data.worlds[0].phobosexportsettings, 'outputMeshtype')

        cscene = inlayout.column(align=True)
        cscene.label(text="Scenes")
        for scenetype in sorted(scenes.scene_types):
            if 'export' in scenes.scene_types[scenetype]:
                typename = "export_scene_" + scenetype
                cscene.prop(bpy.data.worlds[0], typename)

        # c2.prop(expsets, "exportCustomData", text="Export custom data")

        # FIXME: issue with export and import of models with new generic system
        # ec2 = layout.column(align=True)

#        layout.separator()
#        layout.label(text="Baking")
#        layout.operator("phobos.export_bake", text="Bake Robot Model", icon="OUTLINER_OB_ARMATURE")
#        layout.operator("phobos.create_robot_instance", text="Create Robot Lib Instance", icon="RENDERLAYERS")

        # self.layout.prop(expsets, "heightmapMesh", text="export heightmap as mesh")

        layout.separator()
        layout.operator("phobos.export_model", icon="EXPORT")
        layout.operator("phobos.export_scene", icon="WORLD_DATA")


class PhobosImportPanel(bpy.types.Panel):
    """A Custom Panel in the Phobos viewport toolbar"""
    bl_idname = "TOOLS_IMPORT_PT_PHOBOS"
    bl_label = "Import"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Phobos'

    def draw_header(self, context):
        self.layout.label(icon='IMPORT')

    def draw(self, context):
        self.layout.operator("phobos.import_robot_model",
                             text="Import Robot Model", icon="IMPORT")


class PhobosObjectPanel(bpy.types.Panel):
    bl_idname = "phobos.PT_PHOBOS"
    bl_label = "phobos: Object Panel Displaying Custom Properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_category = 'Phobos'

    def draw_header(self, context):
        self.layout.label(icon='SMOOTH')

    def draw(self, context):

        layout = self.layout

        # the following for real pre-defined rather than custom properties
        # row_type.prop(bpy.context.active_object, "type")
        row_type = layout.row()
        row_type.label(icon="OBJECT_DATA")
        # row_type.prop_enum(bpy.context.active_object, '["type"]', "node")
        # row_type.prop_enum(bpy.context.active_object, 'phobostype')
        row_type.prop(bpy.context.active_object, 'phobostype')

        box_props = layout.box()
        try:
            for prop in defs.type_properties[bpy.context.active_object.phobostype]:
                # box_props.label(prop)
                if prop in bpy.context.active_object:
                    box_props.prop(bpy.context.active_object,
                                   '["' + prop + '"]')
        except KeyError:
            print("Key could not be found.")
            # else:
            #    bpy.context.active_object[prop] = defs.type_properties[bpy.context.active_object.phobostype+"_default"]


def get_operator_manuals():
    """Returns a tuple with the Phobos wiki Operator page and pairs of operator
    names and wiki page anchor names to allow for linking from Blender to wiki.
    :return: tuple
    """
    url_manual_prefix = "https://github.com/rock-simulation/phobos/wiki/Operators#"
    url_manual_ops = tuple(('bpy.ops.phobos.' + opname, opname.replace('_', '-'),)
                           for opname in dir(bpy.ops.phobos) if not opname.startswith("__"))
    return url_manual_prefix, url_manual_ops


def register():
    print("Registering phobosgui...")

    bpy.types.Object.phobostype = EnumProperty(
        items=defs.phobostypes,
        name="type",
        description="Phobos object type")

    # Add settings to world to preserve settings for every model
    for meshtype in meshes.mesh_types:
        if 'export' in meshes.mesh_types[meshtype]:
            typename = "export_mesh_" + meshtype
            setattr(bpy.types.World, typename, BoolProperty(
                name=meshtype, default=False))

    for entitytype in entities.entity_types:
        if 'export' in entities.entity_types[entitytype]:
            typename = "export_entity_" + entitytype
            setattr(bpy.types.World, typename, BoolProperty(
                name=entitytype, default=False))

    for scenetype in scenes.scene_types:
        if 'export' in scenes.scene_types[scenetype]:
            typename = "export_scene_" + scenetype
            setattr(bpy.types.World, typename, BoolProperty(
                name=scenetype, default=False))

    # Register classes (cannot be automatic, as panels are placed in gui in the registering order)
    #     for key, classdef in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    #         try:
    #             if classdef.__bases__[0] != bpy.types.Panel:
    #                 bpy.utils.register_class(classdef)
    #         except ValueError:
    #             print('Error with class registration:', key, classdef)
    bpy.utils.register_class(ModelPoseProp)
    bpy.utils.register_class(PhobosPrefs)
    bpy.utils.register_class(PhobosExportSettings)
    # bpy.utils.register_class(Mesh_Export_UIList)
    # bpy.utils.register_class(Models_Poses_UIList)

    bpy.utils.register_class(PhobosToolsPanel)
    bpy.utils.register_class(PhobosModelPanel)
    # bpy.utils.register_class(PhobosScenePanel)
    bpy.utils.register_class(PhobosExportPanel)
    bpy.utils.register_class(PhobosImportPanel)
    bpy.utils.register_class(PhobosObjectPanel)

    bpy.types.World.phobosexportsettings = PointerProperty(
        type=PhobosExportSettings)
    bpy.types.Scene.active_ModelPose = bpy.props.IntProperty(
        name="Index of current pose", default=0, update=showPreview)
    bpy.types.Scene.preview_visible = bpy.props.BoolProperty(
        name="Is the draw preview operator running", default=False)
    bpy.types.Scene.redraw_preview = bpy.props.BoolProperty(
        name="Should we redraw the preview_template", default=False)

    # Add manuals to operator buttons
    bpy.utils.register_manual_map(get_operator_manuals)

    # Read in model and pose data from the respective folders
    # loadModelsAndPoses()
    libraries.register()


def unregister():
    print("Unregistering phobosgui...")

    # Unregister classes
    for key, classdef in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        bpy.utils.unregister_class(classdef)

    # Remove manuals from buttons
    bpy.utils.unregister_manual_map(get_operator_manuals)
