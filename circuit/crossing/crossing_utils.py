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
from picazzo3.wg.chain import TraceChain
import numpy as np
import itertools
import warnings


def collinear(p0, p1, p2, verbose=False):
    x1, y1 = p1[0] - p0[0], p1[1] - p0[1]
    x2, y2 = p2[0] - p0[0], p2[1] - p0[1]

    if np.abs(x1) >= np.abs(y1):
        t = x2 / x1
    else:
        t = y2 / y1

    if verbose:
        print("np.abs(x1 * y2 - x2 * y1) = {}".format(np.abs(x1 * y2 - x2 * y1)))
        print("t={}".format(t))

    return np.abs(x1 * y2 - x2 * y1) < 1e-8 and 0 <= t <= 1


def dp1p2(p0, p1):
    return (p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2


def cut_shape_on_portpairs(shape, port_list_pairs):
    """Cuts a shape in pieces on the port_list.

    Returns
    -------
    cut_shapes : list of shapes
    err_points : list of points where there are errors
    """
    points = shape.points
    pairs_searched = [pair for pair in port_list_pairs]
    cut_shapes = []
    actual_shape = []
    err_points = []
    for cnt_points, (phere, pnext) in enumerate(zip(points[0:-1], points[1:])):
        collinear_pairs = []
        for ppcut in pairs_searched:  # to do check if problem of not straight section
            is_coll = [collinear(phere, pnext, ppcut[cnt]) for cnt in range(2)]
            if any(is_coll) != all(is_coll):
                warnings.warn(
                    "There is a crossing at position {} that can't be connected to. "
                    "Likely there there is no space".format(ppcut))
                err_points.append(ppcut[0].position)
                err_points.append(ppcut[1].position)
            if all(is_coll):
                collinear_pairs.append(ppcut)

        distance_to_p1 = [dp1p2(phere, cp[0]) for cp in collinear_pairs]
        distance_to_p2 = [dp1p2(phere, cp[1]) for cp in collinear_pairs]

        collinear_distance_pairs_sorted_on_left = [(x, d_left)
                                                   for d_left, x in sorted(zip(distance_to_p1, collinear_pairs))]
        collinear_distance_pairs_sorted_on_right = [(x, d_right)
                                                    for d_right, x in sorted(zip(distance_to_p2, collinear_pairs))]

        if len(collinear_distance_pairs_sorted_on_left) > 0:

            for cnt_crossing, (cdpl, cdpr) in enumerate(
                    zip(collinear_distance_pairs_sorted_on_left, collinear_distance_pairs_sorted_on_right)):
                if cnt_crossing == 0:  # First one:
                    if cdpr[1] > cdpl[1]:  # right is further than left
                        actual_shape.extend([phere, cdpl[0][0].position])  # Adding the right point
                        next_point = cdpl[0][1].position
                    else:  # left is further than right
                        actual_shape.extend([phere, cdpl[0][1].position])  # Adding the right point
                        next_point = cdpl[0][0].position

                    cut_shapes.append(actual_shape)
                else:  # Middle ones
                    if cdpr[1] > cdpl[1]:  # right is further than left
                        actual_shape = [next_point, cdpl[0][0].position]  # Adding the right point
                        next_point = cdpl[0][1].position
                    else:  # left is further than right
                        actual_shape = [next_point, cdpl[0][1].position]  # Adding the right point
                        next_point = cdpl[0][0].position
                    cut_shapes.append(actual_shape)

                if cnt_crossing == len(collinear_distance_pairs_sorted_on_left) - 1:

                    if cdpr[1] > cdpl[1]:  # right is further than left
                        actual_shape = [next_point, pnext]  # Adding the right point
                    else:  # left is further than right
                        actual_shape = [next_point, pnext]  # Adding the right point

        else:
            actual_shape.append(phere)
            if cnt_points == len(points) - 2:
                actual_shape.append(pnext)

    cut_shapes.append(actual_shape)  # Add the last remaining bit
    return cut_shapes, err_points


def get_crossing_points(shapes):
    """Detects all the crossing points between shapes.

    Parameters
    ----------
    shapes :

    Return
    ------
    crossings : list of crossings points
    """
    crossings = []
    for s1, s2 in itertools.combinations(shapes, 2):
        crossings += s1.intersections(s2)
    return crossings


def get_new_segments(crossing_instances, original_segment):
    port_list_pairs = []
    new_segments = {}

    for c in crossing_instances:
        port_list_pairs.append((c.ports["in1"], c.ports["out1"]))
        port_list_pairs.append((c.ports["in2"], c.ports["out2"]))
    center_line_shape = original_segment.center_line_shape

    new_shapes, err_points = cut_shape_on_portpairs(center_line_shape, port_list_pairs)

    for cnt, ns in enumerate(new_shapes):
        total_name = "{}_SEG_{}".format(original_segment.name, cnt)
        new_segment_cell = i3.Waveguide(trace_template=original_segment.cell.trace_template, name=total_name)
        new_segment_cell.Layout(shape=ns)
        new_segments[total_name] = new_segment_cell

    if not new_segments:
        print("Something when wrong here")
    return new_segments, err_points


class TraceChainWithCenterLine(TraceChain):
    """Class that only accepts traces that have a method for the center line.
    """

    class Layout(TraceChain.Layout):

        center_line_shape = i3.ListProperty(locked=True)

        def validate_properties(self):
            for cnt, t in enumerate(self.traces):
                if not hasattr(t, "center_line_shape"):
                    raise i3.PropertyValidationError(self,
                                                     "Trace {} has not center_line_shape", {"trace": t,
                                                                                            "type t": type(t),
                                                                                            "Position in trace": cnt})
            return True

        def _default_center_line_shape(self):
            shape = []
            for t in self.traces:
                shape += t.center_line_shape

            return shape
