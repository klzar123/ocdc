# Copyright (C) 2020 Luceda Photonics
# This version of Luceda Academy and related packages
# (hereafter referred to as Luceda Academy) is distributed under a proprietary License by Luceda
# It does allow you to develop and distribute add-ons or plug-ins, but does
# not allow redistribution of Luceda Academy  itself (in original or modified form).
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.
#
# For the details of the licensing contract and the conditions under which
# you may use this software, we refer to the
# EULA which was distributed along with this program.
# It is located in the root of the distribution folder.

from ipkiss3 import all as i3
from ipkiss.geometry.shapes.basic import ShapeBend
from ipkiss.constants import RAD2DEG
import numpy as np


class TwoPointShape(i3.Shape):
    """Shape of two points with the correct face angles.
    """
    start_point = i3.Coord2Property()
    end_point = i3.Coord2Property()
    radius = i3.DefinitionProperty(default=None)

    def _default_radius(self):
        return None

    def _default_end_face_angle(self):
        return self.end_point.angle_deg(self.start_point)

    def _default_start_face_angle(self):
        return self.start_point.angle_deg(self.end_point)

    def define_points(self, pts):
        return [self.start_point, self.end_point]


def AngledShapeBendRelative(start_point=(0.0, 0.0),
                            radius=1.0,
                            input_angle=0.0,
                            angle_amount=90.0,
                            angle_step=i3.TECH.METRICS.ANGLE_STEP):
    """Shape Bend Relative but with correct face angles.
    """
    clockwise = bool(angle_amount < 0)
    bend = ShapeBend(start_point=start_point,
                     radius=radius,
                     input_angle=input_angle,
                     output_angle=input_angle + angle_amount,
                     clockwise=clockwise,
                     angle_step=angle_step,
                     start_face_angle=input_angle,
                     end_face_angle=input_angle + angle_amount
                     )
    bend.snap_to_grid()
    return bend


def get_rounded_shapes(shape, radius=5.0):
    """Returns shapes with rounding applied snapped to grid and with correct phase angles as well as the bend_radii^-1.
    """
    rounded_shape = i3.ShapeRound(original_shape=shape, radius=radius)
    (Swsa, R) = rounded_shape.__original_shape_without_straight_angles__()
    shapes = []
    c = Swsa.points
    (r, tt, t, a1, a2, L, D) = rounded_shape.__radii_and_turns__(Swsa)
    # create the bends
    # bend start points (whereby we can ignore the 1st and last point for an open shape)
    Swsa = c - np.column_stack((L * np.cos(a1), L * np.sin(a1)))

    for i in range(1, len(c) - 1):  # ignore first and last point in matrix
        sh = AngledShapeBendRelative(start_point=Swsa[i],
                                     radius=r[i],
                                     input_angle=a1[i] * RAD2DEG,
                                     angle_amount=t[i] * RAD2DEG,
                                     angle_step=rounded_shape.angle_step)
        shapes.append(sh)

    if len(shapes) > 0:
        shapes.append(TwoPointShape(start_point=shapes[-1].points[-1], end_point=c[-1]))
        tot_shape = [TwoPointShape(start_point=c[0], end_point=shapes[0].points[0])]
    else:
        tot_shape = [TwoPointShape(start_point=c[0], end_point=c[1])]

    for sh in shapes:
        lp = tot_shape[-1].points[-1]
        nsp = sh.points[0]
        if np.any(lp != nsp):
            tot_shape.append(TwoPointShape(start_point=lp, end_point=nsp))
        tot_shape.append(sh)

    return tot_shape
