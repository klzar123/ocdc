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

from picazzo3.wg.chain.cell import TraceChain
from .shapes import get_rounded_shapes
from ipkiss3 import all as i3


def get_offset_template(trace_template, offset):
    new_template = trace_template.modified_copy(name=trace_template.name + "{}".format(offset))
    windows = trace_template.get_default_view(i3.LayoutView).windows
    new_windows = []
    for w in windows:
        nw = w.modified_copy(start_offset=w.start_offset + offset, end_offset=w.end_offset + offset)
        new_windows.append(nw)

    new_template.get_default_view(i3.LayoutView).set(windows=new_windows)

    return new_template


class RoundedWaveguideOffset(TraceChain):
    """Waveguide with offset bends to reduce bending losses.
    In this implementation, all the bends have the same offset.
    """
    route = i3.ShapeProperty(doc="Original route")
    trace_template = i3.TraceTemplateProperty(doc="Original trace_template")
    trace_template_offsetp = i3.TraceTemplateProperty(doc="Offsetted trace template ")
    trace_template_offsetm = i3.TraceTemplateProperty(doc="Offsetted trace template ")
    bend_radius = i3.PositiveNumberProperty("Bend radius (uniform over the entire guide")
    offset = i3.PositiveNumberProperty(default=0.1)

    def _default_trace_template(self):
        from si_fab.components.waveguides.wire import SiWireWaveguideTemplate
        return SiWireWaveguideTemplate(name=self.name + "tt")

    def _default_trace_template_offsetp(self):
        tt = get_offset_template(trace_template=self.trace_template, offset=self.offset)
        return tt

    def _default_trace_template_offsetm(self):
        tt = get_offset_template(trace_template=self.trace_template, offset=-self.offset)
        return tt

    def _default_traces(self):
        shapes = get_rounded_shapes(shape=self.route, radius=self.bend_radius)
        wavs = []

        for cnt, sh in enumerate(shapes):

            if sh.radius is None:
                tt = self.trace_template
            elif sh.clockwise:
                tt = self.trace_template_offsetm
            elif not sh.clockwise:
                tt = self.trace_template_offsetp
            else:
                raise Exception("Could not find the trace template")

            wav = i3.Waveguide(trace_template=tt, name=self.name + "_{}".format(cnt))
            wav.Layout(shape=sh)
            wavs.append(wav)
        return wavs

    class Layout(TraceChain.Layout):

        def _default_auto_transform(self):
            return False

        def _default_flatten(self):
            return True
