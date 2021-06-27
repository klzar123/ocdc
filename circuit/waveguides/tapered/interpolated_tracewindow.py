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
from ipkiss3.pcell.trace.window.window import _TraceWindow
from ipkiss.geometry.shape import Shape
import numpy as np
# from patch import ShapeVariableOffset, BoundaryPath
from ipkiss3.all import ShapeVariableOffset, BoundaryPath


def get_path_shape_with_termination_offsets(shape, window_start, window_end, termination_offsets, interpolate_fn):
    """Calculates the path shape including the additional points in the termination.
    """
    red_shape = Shape(shape).remove_identicals(
    )  # FIXME: can we make this more efficient? We only need the first and last segment.

    if len(red_shape) <= 1:
        return Shape()

    (sfa, efa) = shape.get_face_angles()

    # Get the termination shapes of the waveguides
    C_start = window_start.get_termination_shape(offsets=termination_offsets,
                                                 face_angle_deg=sfa,
                                                 coordinate=shape[0],
                                                 inclusive=False)

    C_end = window_end.get_termination_shape(offsets=termination_offsets,
                                             face_angle_deg=efa,
                                             coordinate=shape[-1],
                                             inclusive=False)

    # Calculate the offsetted shapes using ShapeVariableOffset
    # we need to do this for each side of the waveguide.

    # ratios contain values between 0 and 1, and indicate the position
    # relative to the start and end point of the shape.
    distances = shape.distances()
    ratios = np.zeros(len(distances))
    ratios[1:] = np.cumsum(distances[0:-1]) / shape.length()
    ratios[-1] = 1.0

    C1_offset_start = min(window_start.start_offset, window_start.end_offset)
    C1_offset_end = min(window_end.start_offset, window_end.end_offset)
    C1_offsets = [interpolate_fn(C1_offset_start, C1_offset_end, ratio)
                  for ratio in ratios]

    C1 = ShapeVariableOffset(original_shape=shape,
                             offsets=C1_offsets)

    C2_offset_start = max(window_start.start_offset, window_start.end_offset)
    C2_offset_end = max(window_end.start_offset, window_end.end_offset)
    C2_offsets = [interpolate_fn(C2_offset_start, C2_offset_end, ratio)
                  for ratio in ratios]

    C2 = ShapeVariableOffset(original_shape=shape,
                             offsets=C2_offsets)

    # Concatenate all shapes to form the path.
    b_shape = C1 + C_end + C2.reversed() + C_start.reversed()
    b_shape.closed = True
    return b_shape


class InterpolatedTraceWindow(_TraceWindow):
    """A TraceWindow that helps to create a waveguide that interpolates between 2 TraceWindows.
    """
    window_start = i3.DefinitionProperty(i3.RestrictType(i3.PathTraceWindow),
                                         doc="Window describing the waveguide at the start")
    window_end = i3.DefinitionProperty(i3.RestrictType(i3.PathTraceWindow),
                                       doc="Window describing the waveguide at the end")

    interpolate_fn = i3.CallableProperty(doc="function to interpolate the windows")

    def _default_interpolate_fn(self):
        # linear interpolation by default
        return lambda start, end, r: (1 - r) * start + r * end

    layer = i3.LayerProperty()

    def _default_layer(self):
        # By default we reuse the layer of window_start
        return self.window_start.layer

    line_width = i3.NonNegativeNumberProperty()

    def _default_line_width(self):
        # By default we reuse the line_width of window_start
        # return self.window_start.line_width
        return self.window_start.end_offset - self.window_start.start_offset

    def get_elements_from_shape(self, shape, termination_offsets=[], **kwargs):
        from ipkiss.primitives.elements import ElementList
        if shape.length() > 0.0:
            window_start = self.window_start
            window_end = self.window_end
            interpolate_fn = self.interpolate_fn

            path_shape = get_path_shape_with_termination_offsets(shape,
                                                                 window_start,
                                                                 window_end,
                                                                 termination_offsets,
                                                                 interpolate_fn)

            # calculate the centerline of the shape.
            distances = shape.distances()
            ratios = np.zeros(len(distances))
            ratios[1:] = np.cumsum(distances[0:-1]) / shape.length()
            ratios[-1] = 1.0
            center_offset_start = 0.5 * (window_start.start_offset + window_start.end_offset)
            center_offset_end = 0.5 * (window_end.start_offset + window_end.end_offset)
            center_offsets = [interpolate_fn(center_offset_start, center_offset_end, ratio)
                              for ratio in ratios]

            centerline_sh = ShapeVariableOffset(original_shape=shape,
                                                offsets=center_offsets)

            elems = [BoundaryPath(layer=self.layer,
                                  shape=path_shape,
                                  centerline_shape=centerline_sh,
                                  path_line_width=self.line_width)]
        else:
            elems = []

        return ElementList(elems)

    def get_elements_from_trace(self, trace):
        shape = getattr(trace, self.shape_property_name)
        return self.get_elements_from_shape(shape=shape,
                                            termination_offsets=trace._get_offset_list())
