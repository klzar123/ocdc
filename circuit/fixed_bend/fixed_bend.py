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

# flake8: noqa

if __name__ == "__main__":
    import si_fab.all as pdk

from ipkiss3 import all as i3
from circuit.route_through_control_points import RouteManhattanControlPoints
from picazzo3.wg.chain import TraceChain
import numpy as np


class FixedBendWaveguide(TraceChain):
    """Waveguide that uses a fixed bend cell for each 90 degree bend.
    """
    bend = i3.ChildCellProperty(doc="pcell for the 90 degree bend")
    route = i3.ShapeProperty(doc="Route used for the centerl line")
    taper_length = i3.PositiveNumberProperty(default=10.0, doc="Taper length of fort the transitions")
    width_wide = i3.PositiveNumberProperty(default=3.0, doc="Width of the wide waveguide")

    def _default_bend(self):
        wav = i3.RoundedWaveguide()
        wav.Layout(shape=[(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)], bend_radius=5.0)
        return wav

    def _default_n_o_traces(self):
        return len(self.get_child_instances())

    def _default_traces(self):
        return [i.reference for i in self.get_child_instances().itervalues()]

    @i3.cache()
    def get_child_instances(self):

        import warnings
        with warnings.catch_warnings():
            # LA issue #180.
            warnings.simplefilter('ignore', category=DeprecationWarning)

            insts = i3.InstanceDict()
            cnt = 1
            last_point = self.route[0]
            for pos, turn, angle in zip(self.route, self.route.turns_deg(), self.route.angles_deg()):
                if turn % 90 == 0.0 and turn % 180 != 0.0:
                    bend_radius = self.bend.get_default_view(i3.LayoutView).bend_radius
                    pos_output = pos.move_polar_copy(distance=bend_radius, angle=angle)
                    pos_input = pos.move_polar_copy(distance=bend_radius, angle=angle - turn + 180.0)
                    angle_output = angle + 180.0
                    from ipkiss.geometry.vector import vector_match_transform
                    transnm = vector_match_transform(self.bend.get_default_view(i3.LayoutView).ports["out"],
                                                     i3.Vector(position=pos_output, angle_deg=angle_output))
                    transm = vector_match_transform(self.bend.get_default_view(i3.LayoutView).ports["out"],
                                                    i3.Vector(position=pos_output, angle_deg=angle_output), mirrored=True)
                    if self.bend.get_default_view(i3.LayoutView).ports["in"].transform_copy(
                            transformation=transnm).position.distance(pos_input) < 0.1:
                        t = transnm
                    else:
                        t = transm

                    bend_inst = i3.SRef(name="W{}".format(cnt + 1), reference=self.bend, transformation=t)

                    wav_in = i3.ExpandedWaveguide(trace_template=self.bend.trace_template,
                                                  name=self.name + "_W{}".format(cnt))
                    wav_in.Layout(bend_radius=bend_radius, shape=[last_point, bend_inst.ports["in"]],
                                  expanded_width=self.width_wide,
                                  taper_length=self.taper_length,
                                  )

                    insts += i3.SRef(name="_W{}".format(cnt), reference=wav_in)
                    insts += bend_inst

                    cnt += 2
                    last_point = bend_inst.ports["out"]

            wav_in = i3.ExpandedWaveguide(trace_template=self.bend.trace_template, name=self.name + "_W{}".format(cnt))
            wav_in.Layout(bend_radius=bend_radius, shape=[last_point, self.route[-1]],
                          expanded_width=self.width_wide,
                          taper_length=self.taper_length,
                          )
            insts += i3.SRef(name="W{}".format(cnt), reference=wav_in)

        return insts

    class Layout(TraceChain.Layout):
        def _generate_instances(self, insts):
            return self.cell.get_child_instances()


if __name__ == "__main__":
    input_port = i3.OpticalPort(name="grating_in", position=(0.0, 0.0), angle=0.0)
    output_port = i3.OpticalPort(name="grating_out", position=(300., 300.0), angle=180.0)
    bend_radius = 5.0
    route = RouteManhattanControlPoints(input_port=input_port, output_port=output_port, control_points=[
        (100.0, 150.0), (100, 300), (200, 400)], bend_radius=bend_radius)
    cell = FixedBendWaveguide(route=route)
    lv = cell.Layout()
    lv.visualize(annotate=True)
    lv.write_gdsii("test_gdsii_bend.gds")
    print("The total waveguide length is {} um.".format(lv.trace_length()))

    wavs = np.linspace(1.5, 1.6, 1001)
    cm = cell.CircuitModel()
    S = cm.get_smatrix(wavelengths=wavs)
    import pylab as plt

    plt.plot(wavs, np.unwrap(np.angle(S["in", "out"])))

    plt.xlabel("wavelengths")
    plt.ylabel("phase")
    plt.show()
