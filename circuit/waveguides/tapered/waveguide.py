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
from interpolated_tracewindow import InterpolatedTraceWindow
from ..generic.trace import GenericWaveguide, GenericWaveguideTemplate, generate_wg_model
import numpy as np


class WaveguideBetweenTraceTemplates(GenericWaveguide):
    """A waveguide that interpolates between 2 WindowWaveguideTemplates.
    """

    class Layout(GenericWaveguide.Layout):

        def _generate_ports(self, ports):
            ports = super(GenericWaveguide.Layout, self)._generate_ports(ports)
            from ipkiss.plugins.photonics.port.port_list import OpticalPortList
            new_ports = OpticalPortList()
            ttstart = ports["in"].trace_template.trace_template_start
            ttend = ports["in"].trace_template.trace_template_end

            new_ports += ports["in"].modified_copy(trace_template=ttstart)
            new_ports += ports["out"].modified_copy(trace_template=ttend)

            return new_ports

    class CircuitModel(GenericWaveguide.CircuitModel):

        def _generate_model(self):
            tts_cm = self.cell.template.trace_template_start.get_default_view(i3.CircuitModelView)
            tte_cm = self.cell.template.trace_template_end.get_default_view(i3.CircuitModelView)

            lv = self.cell.get_default_view(i3.LayoutView)

            assert(len(tte_cm.wavelengths) == len(tte_cm.wavelengths))
            for w1, w2 in zip(tts_cm.wavelengths, tte_cm.wavelengths):
                if w1 != w2:
                    raise Exception("The wavelengths of the circuit models of"
                                    "both traces templates making the tapered waveguide need to be identical")

            neffs = np.array([0.5 * np.array(tts_cm.get_n_eff(i3.Environment(wavelength=wl))) +
                              0.5 * np.array(tte_cm.get_n_eff(i3.Environment(wavelength=wl)))
                              for wl in tts_cm.wavelengths])

            phase_error = np.array(
                [0.5 * (pes + pee) for pes, pee in zip(tts_cm.get_phase_error(), tte_cm.get_phase_error())])

            model_class = generate_wg_model(n_modes=len(tte_cm.n_eff_values))
            return model_class(length=lv.trace_length,  # calculated from the layout automatically
                               n_effs=neffs,
                               wavelengths=tts_cm.wavelengths,
                               phase_error=phase_error)


class InterpolatedWaveguideTemplate(GenericWaveguideTemplate):
    """Waveguide template with a start template and a end trace_template.
    """
    _templated_class = WaveguideBetweenTraceTemplates
    trace_template_start = i3.TraceTemplateProperty()
    trace_template_end = i3.TraceTemplateProperty()

    class Layout(i3.WindowWaveguideTemplate.Layout):

        def _default_windows(self):
            windows = []
            for ws, we in zip(self.trace_template_start.windows, self.trace_template_end.windows):
                windows.append(InterpolatedTraceWindow(window_start=ws, window_end=we))

            return windows
