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
import CSiP180Al.all as pdk
import ipkiss3.all as i3
from phaseshifter import HeaterBroadBandPhaseErrorCompactModel
import numpy as np

r_sheet = 500e-3  # OhmSq


class HeatedWaveguide(i3.Waveguide):
    """ Phase shifter waveguide with heater layers on each side.

    The heater will follow the shape of the waveguide.
    Metal contacts are placed at the start and end of the heater.
    """

    _name_prefix = "HEATED_WAVEGUIDE"
    heater_width = i3.PositiveNumberProperty(default=0.6, doc="Width of the heater")
    heater_offset = i3.PositiveNumberProperty(default=1.0, doc="Offset of the heaters from the waveguide center")
    heater_length = i3.PositiveNumberProperty(default=200.0, doc="Length of the heater")
    m1_width = i3.PositiveNumberProperty(default=1.0, doc="Width of the M1 contact")
    m1_length = i3.PositiveNumberProperty(default=3.0, doc="Length of the M1 contact")

    def _default_trace_template(self):
        return pdk.SWG450_CTE()

    class Layout(i3.Waveguide.Layout):

        def _default_shape(self):
            #return i3.Shape([(0.0, 0.0), (30 * self.m1_length, 0.0)])

            return i3.Shape([(0.0, 0.0), (self.heater_length, 0.0)])

        def _generate_elements(self, elems):
            elems = super(HeatedWaveguide.Layout, self)._generate_elements(elems)

            m1_hw = self.m1_width / 2.
            heater_hw = self.heater_width / 2.
            heater_offset = self.heater_offset

            # Draw heater
            # Use windows which we extrude along the generic waveguide shape
            heater_windows = [
                i3.PathTraceWindow(
                    start_offset=i * heater_offset - heater_hw,
                    end_offset=i * heater_offset + heater_hw,
                    layer=i3.TECH.PPLAYER.HEATER.DRW
                ) for i in [-1, 1]
            ]

            center_line = self.center_line_shape
            for h in heater_windows:
                elems += h.get_elements_from_shape(shape=center_line)

            m_windows = [
                i3.PathTraceWindow(
                    start_offset=-heater_offset - m1_hw,
                    end_offset=heater_offset + m1_hw,
                    layer=i3.TECH.PPLAYER.M1.DRW
                )
            ]
            # cut the first and last part of the heater shape and put the metal window on top of it
            trim_length = center_line.length() - self.m1_length
            endpoint_shapes = [
                i3.ShapeShorten(original_shape=center_line,
                                trim_lengths=(0.0, trim_length)),
                i3.ShapeShorten(original_shape=center_line,
                                trim_lengths=(trim_length, 0.0))
            ]
            for w in m_windows:
                for s in endpoint_shapes:
                    elems += w.get_elements_from_shape(shape=s)
            return elems

        def _generate_ports(self, ports):
            ports = super(HeatedWaveguide.Layout, self)._generate_ports(ports)
            metal_pos = [p.position.move_polar_copy(angle=p.angle + 180.0,
                                                    distance=self.m1_length / 2.0)
                         for p in [ports["in"], ports["out"]]]

            ports += i3.ElectricalPort(name='elec1', position=metal_pos[0], layer=i3.TECH.PPLAYER.M1.DRW)
            ports += i3.ElectricalPort(name='elec2', position=metal_pos[1], layer=i3.TECH.PPLAYER.M1.DRW)
            return ports

    class CircuitModel(i3.CircuitModelView):
        p_pi_sq = i3.PositiveNumberProperty(default=100e-3, doc="Power needed for a pi phase shift on a square [W]")

        def _generate_model(self):
            template = self.trace_template
            wavelengths = template.wavelengths
            neffs = np.array([template.get_n_eff(i3.Environment(wavelength=wl)) for wl in wavelengths])
            length = self.cell.get_default_view(i3.LayoutView).trace_length()
            return HeaterBroadBandPhaseErrorCompactModel(
                length=length,
                width=2 * self.heater_width,  # parallel -> half resistance
                n_effs=neffs,
                wavelengths=wavelengths,
                phase_error=self.trace_template.get_phase_error(),
                p_pi_sq=self.p_pi_sq,
            )

    class Netlist(i3.NetlistFromLayout):
        pass

if __name__=="__main__":

    ht = HeatedWaveguide(heater_width=0.6,
                         heater_offset=1.0,
                         m1_width=1.0,
                         m1_length=3.0)
    ht_ly = ht.Layout
    ht.Layout.visualize(annotate=False)

    #ht_lv = ht.Layout(shape=[(0.0, 0.0), (40.0, 0.0)])
    #ht_lv.visualize(annotate=True)