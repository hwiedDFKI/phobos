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
model_previews = {}
categories = set([])


def getModelListForEnumProperty(self, context):
    ''' Returns a list of (str, str, str) elements which contains the models
    contained in the currently selected model category.
    If there are no model categories (i.e. '-') return ('-', '-', '-').
    '''
    category = context.window_manager.category
    if category == '-' or category == '':
        return [('-',) * 3]
    return sorted(model_previews[category].enum_items)


def getCategoriesForEnumProperty(self, context):
    ''' Return a list of (str, str, str) elements, each referring to an
    available category in the model library.
    If there are no categories return ('-', '-', '-').
    '''
    if len(categories) == 0:
        return [('-',) * 3]
    return [(item,) * 3 for item in categories]


def compileModelList():
    from bpy.props import EnumProperty
    from bpy.types import WindowManager
    # DOCU missing some docstring
    log("Compiling model list from local library...", "INFO")

    # clear old preview collections
    for previews in model_previews.values():
        bpy.utils.previews.remove(previews)
    model_previews.clear()
    model_data.clear()

    rootpath = bpy.context.user_preferences.addons["phobos"].preferences.modelsfolder
    i = 0
    if rootpath == '' or not os.path.exists(rootpath):
        log('Model library folder does not exist.')
        return

    # parse the model folder
    for category in os.listdir(rootpath):
        categorypath = os.path.join(rootpath, category)
        # skip all non folders
        if not os.path.isdir(categorypath):
            continue

        # initialise new dictionaries
        model_data[category] = {}
        newpreviewcollection = bpy.utils.previews.new()
        enum_items = []

        # parse category folder
        for modelname in os.listdir(categorypath):
            modelpath = os.path.join(categorypath, modelname)

            # check for valid blender savefile in the model folder
            if os.path.exists(os.path.join(modelpath, 'blender', modelname+'.blend')):
                model_data[category][modelname] = {'path': modelpath}

                # use existing thumbnail if available
                if os.path.exists(os.path.join(modelpath, 'thumbnails')):
                    preview = newpreviewcollection.load(modelname, os.path.join(modelpath, 'thumbnails', modelname+'.png'), 'IMAGE')
                    log("Adding model to preview: " + os.path.join(modelpath, 'thumbnails', modelname+'.png'),
                        'DEBUG', 'compileModelList')
                # otherwise create one from the blend file
                else:
                    preview = newpreviewcollection.load(modelname, os.path.join(modelpath, 'blender', modelname + '.blend'), 'BLEND')
                    log("Adding model to preview: " + os.path.join(os.path.join(modelpath, 'blender', modelname + '.blend')),
                        'DEBUG', 'compileModelList')
                enum_items.append((modelname, modelname, "", preview.icon_id, i))
                i += 1
                categories.add(category)
        # save the category
        newpreviewcollection.enum_items = enum_items
        model_previews[category] = newpreviewcollection

    # reregister the enumproperty to ensure new items are displayed
    WindowManager.modelpreview = EnumProperty(items=getModelListForEnumProperty, name='Model')
    WindowManager.category = EnumProperty(items=getCategoriesForEnumProperty, name='Category')


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
    for previews in model_previews.values():
        bpy.utils.previews.remove(previews)
    model_previews.clear()
    model_data.clear()
