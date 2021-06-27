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

from __future__ import division
from route_through_control_points import RouteManhattanControlPoints
import warnings
from ipkiss3 import all as i3
from ipkiss3.constants import DEG2RAD
import math
from ipkiss.geometry.shape_info import distance
import numpy as np
from scipy import interpolate


def multiple_entries(input):
    """Returns lists of non-unique elements in a sortable list.
    """
    seen = set()
    multiples = set()
    for elem in input:
        if elem in seen and elem not in multiples:
            multiples.add(elem)
        seen.add(elem)

    return multiples


def get_port_from_interface(port_id, inst_dict):
    instance_name = port_id.split(":")[0]
    port_name = port_id.split(":")[1]
    if instance_name not in inst_dict.keys():
        raise Exception("Instance {} does not exist - please check your childcells".format(instance_name))
    pnames = [p.name for p in inst_dict[instance_name].ports]
    if port_name not in pnames:
        raise Exception(
            "Port {} does not exist on instance {} - the available ports are {}".format(port_name, instance_name,
                                                                                        pnames))
    return inst_dict[instance_name].ports[port_name]


def get_template(start_port, end_port):
    if start_port is not None:
        trace_template = start_port.trace_template
    elif end_port is not None:
        trace_template = end_port.trace_template
    else:
        trace_template = i3.TECH.PCELLS.WG.DEFAULT

    if start_port is not None and end_port is not None:
        cw1 = start_port.trace_template.core_width
        cw2 = end_port.trace_template.core_width
        cw3 = trace_template.core_width

        if cw3 != cw1:
            warnings.warn("A waveguide core may not match at location {}".format(start_port.position))

        if cw3 != cw2:
            warnings.warn("A waveguide core may not match at location {}".format(end_port.position))

    return trace_template


def get_bend_size(rounding_algorithm, bend_radius, angle):
    """Returns the size of a bend with an arbitrary angle. The size is expressed as a tuple of two lengths:
    The length from the bend control point to the interface with the previous and next straight segment.
    If the bend is asymmetric, the reverse bend will switch the values.
    """
    if angle == 0.0:
        return 0, 0
    s = i3.Shape([(-100 * bend_radius, 0),
                  (0, 0),
                  (100 * bend_radius * math.cos(angle * DEG2RAD), 100 * bend_radius * math.sin(angle * DEG2RAD))])

    s = rounding_algorithm(original_shape=s,
                           radius=bend_radius)
    if len(s) > 1:
        return distance(s[-2]), distance(s[1])  # L2,L1
    else:
        return 0, 0


def get_bezier_ra(adiabatic_angle=10.0):
    class RA(i3.ShapeRoundAdiabaticSpline):
        def _default_adiabatic_angles(self):
            return adiabatic_angle, adiabatic_angle

    return RA


def get_max_bend_radius(rounding_algorithm, dist, angle=90.0):
    Rtest = 100.0
    bs = min(get_bend_size(rounding_algorithm=rounding_algorithm, bend_radius=Rtest, angle=angle))
    coef = bs / Rtest
    return dist / coef * 0.99


def line(p1, p2):
    A = (p1[1] - p2[1])
    B = (p2[0] - p1[0])
    C = (p1[0] * p2[1] - p2[0] * p1[1])
    return A, B, -C


def get_D(L1, L2):
    D = L1[0] * L2[1] - L1[1] * L2[0]
    return D


def get_D_ports(start_port, end_port):
    L1 = line(start_port.position, start_port.position.move_polar_copy(100.0, start_port.angle))
    L2 = line(end_port.position.move_polar_copy(100.0, end_port.angle), end_port.position)
    D = get_D(L1, L2)
    return D


def intersection(L1, L2):
    D = get_D(L1, L2)
    Dx = L1[2] * L2[1] - L1[1] * L2[2]
    Dy = L1[0] * L2[2] - L1[2] * L2[0]
    if D != 0:
        x = Dx / D
        y = Dy / D
        return x, y
    else:
        return None


def get_curvature_with_spline(shape):
    """Returns the curvature (1/bend_radius) of the shape for each point in the shape.

    Parameters
    -----------
    shape : i3.Shape

    Returns
    -------
    curvature : list of floats
        List of bend radii as a function of lengths
    """

    if hasattr(shape, '_get_spline_tck_u'):
        tck, ucontrol, usample = shape._get_spline_tck_u()
    else:
        shape2 = i3.ShapeFitNaturalCubicSpline(original_shape=shape)
        tck, ucontrol, usample = shape2._get_spline_tck_u()

    dt = interpolate.splev(usample, tck, 1)
    ddt = interpolate.splev(usample, tck, 2)
    curvature = np.abs(dt[0] * ddt[1] - ddt[0] * dt[1]) / (dt[0] * dt[0] + dt[1] * dt[1]) ** 1.5
    return curvature
