#!/usr/bin/python
# coding=utf-8

"""
.. module:: phobos.io.libraries.models.py
    :platform: Unix, Windows, Mac
    :synopsis: This module contains operators import/export

.. moduleauthor:: Kai von Szadowski, Simon Reichel

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
"""

import os
import bpy
import bpy.utils.previews
import phobos.utils.naming as nUtils
import phobos.utils.io as ioUtils
from phobos.phoboslog import log
from bpy.props import StringProperty, BoolProperty

model_data = {}
preview_collections = {}


def getModelListForEnumProperty(self, context):
    # DOCU missing some docstring
    category = context.window_manager.category
    try:
        items = sorted(preview_collections[category].enum_items)
    except KeyError:
        items = []
    return items


def getCategoriesForEnumProperty(self, context):
    # DOCU missing some docstring
    try:
        categories = [(category,) * 3 for category in sorted(preview_collections.keys())]
    except:
        log('Unable to compile category list.', 'ERROR')
        categories = []
    return categories


def compileModelList():
    # DOCU missing some docstring
    log("Compiling model list from local library...", "INFO", 'compileModelList')
    for previews in preview_collections.values():
        bpy.utils.previews.remove(previews)
    preview_collections.clear()
    model_data.clear()

    rootpath = bpy.context.user_preferences.addons["phobos"].preferences.modelsfolder
    i = 0
    if rootpath != '' and os.path.exists(rootpath):
        for category in os.listdir(rootpath):
            model_data[category] = {}
            newpreviewcollection = bpy.utils.previews.new()
            enum_items = []
            categorypath = os.path.join(rootpath, category)
            for modelname in os.listdir(categorypath):
                modelpath = os.path.join(categorypath, modelname)
                if os.path.exists(os.path.join(modelpath, 'blender', modelname+'.blend')):
                    model_data[category][modelname] = {'path': modelpath}
                    if os.path.exists(os.path.join(modelpath, 'thumbnails')):
                        preview = newpreviewcollection.load(modelname, os.path.join(modelpath, 'thumbnails', modelname+'.png'), 'IMAGE')
                        log("Adding model to path: " + os.path.join(modelpath, 'thumbnails', modelname+'.png'),
                            'DEBUG', 'compileModelList')
                    else:
                        preview = newpreviewcollection.load(modelname, os.path.join(modelpath, 'blender', modelname + '.blend'), 'BLEND')
                        log("Adding model to path: " + os.path.join(os.path.join(modelpath, 'blender', modelname + '.blend')),
                            'DEBUG', 'compileModelList')
                    enum_items.append((modelname, modelname, "", preview.icon_id, i))
                    i += 1
            newpreviewcollection.enum_items = enum_items
            preview_collections[category] = newpreviewcollection
    else:
        log('Model library folder does not exist.')


class UpdateModelLibraryOperator(bpy.types.Operator):
    """Update Model Library"""
    bl_idname = "phobos.update_model_library"
    bl_label = "Update Library"

    def execute(self, context):
        compileModelList()
        return {'FINISHED'}


class ImportModelFromLibraryOperator(bpy.types.Operator):
    # DOCU add some docstring
    bl_idname = "phobos.import_model_from_library"
    bl_label = "Import Model"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'FILE'
    bl_options = {'REGISTER', 'UNDO'}

    namespace = StringProperty(
        name="Namespace",
        default="",
        description="Namespace with which to wrap the imported model. Avoids duplicate names of Blender objects."
    )

    use_prefix = BoolProperty(
       name='Use prefix',
       default=True,
       description="Import model with fixed prefixed instead of removable namespace.")

    #as_reference = BoolProperty(
    #    name='Import reference'
    #    default=False,
    #    description="Import model as reference to original model instead of importing all elements.")

    def invoke(self, context, event):
        modelname = context.window_manager.modelpreview
        self.namespace = modelname
        # prevent duplicate names
        namespaces = nUtils.gatherNamespaces('__' if self.use_prefix else '::')
        if modelname in namespaces:
            i = 1
            self.namespace = modelname + '_' + str(i)
            while self.namespace in namespaces:
                i += 1
                self.namespace = modelname + '_' + str(i)
        return context.window_manager.invoke_props_dialog(self, width=500)


    def execute(self, context):
        wm = context.window_manager
        filepath = os.path.join(model_data[wm.category][wm.modelpreview]['path'],
                                'blender', wm.modelpreview+'.blend')
        if ioUtils.importBlenderModel(filepath, self.namespace, self.use_prefix):
            return {'FINISHED'}
        else:
            log("Model " + wm.modelpreview + " could not be loaded from library: No valid .blend file.",
                "ERROR")
            return {'CANCELLED'}


def register():
    from bpy.types import WindowManager
    from bpy.props import (
            StringProperty,
            EnumProperty,
            BoolProperty
            )
    WindowManager.modelpreview = EnumProperty(items=getModelListForEnumProperty, name='Model')
    WindowManager.category = EnumProperty(items=getCategoriesForEnumProperty, name='Category')
    compileModelList()


def unregister():
    for previews in preview_collections.values():
        bpy.utils.previews.remove(previews)
    preview_collections.clear()
    model_data.clear()
