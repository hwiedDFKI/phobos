#!/usr/bin/python
# coding=utf-8

"""
.. module:: phobos.export.light
    :platform: Unix, Windows, Mac
    :synopsis: TODO: INSERT TEXT HERE

.. moduleauthor:: Kai von Szadkowski

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

File light.py

Created on 12 Sep 2016
"""

import phobos.model.models as models
import phobos.utils.selection as sUtils
from phobos.phoboslog import log


def deriveEntity(light, outpath):
    """This function handles a light entity in a scene to export it

    :param entity: The lights root object.
    :type entity: bpy.types.Object
    :param outpath: The path to export to. Not used for light entity
    :type outpath: str
    :param savetosubfolder: If True data will be exported into subfolders. Not used for light entity
    :type savetosubfolder: bool
    :return: dict - An entry for the scenes entitiesList

    """
    log("Exporting " + light["entity/name"] + " as a light entity", "INFO")
    entitypose = models.deriveObjectPose(light)
    lightobj = sUtils.getImmediateChildren(light)[0]
    color = lightobj.data.color
    entity = {"name": light["entity/name"],
             "type": "light",
             "light_type": "spotlight" if lightobj.data.type == "SPOT" else "omnilight",
             "anchor": light["anchor"] if "anchor" in light else "none",
             "color": {"diffuse": [color.r, color.g, color.b],
                       "use_specular": lightobj.data.use_specular  # only specular information currently available
                       },
             "position": entitypose["translation"],
             "rotation": entitypose["rotation_quaternion"]
             }
    if entity["light_type"] == "spotlight":
        entity["angle"] = lightobj.data.spot_size
    return entity



#  registering import/export functions of types with Phobos
entity_type_dict = {'light': {'derive': deriveEntity}
                    }
