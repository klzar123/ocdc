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

from picazzo3.traces.wire_wg.transitions import LinearWindowWaveguideTransition
from ipkiss.technology import get_technology
from ipkiss3.pcell.layout.view import LayoutView
from ipkiss3.simulation.engines.caphe_circuit_sim.pcell_views.caphemodel import CircuitModelView
from pysics.optics.environment import Environment
import numpy as np
from .trace import generate_wg_model

TECH = get_technology()


class GenericTransition(LinearWindowWaveguideTransition):
    class CircuitModel(CircuitModelView):

        def _generate_model(self):
            tts_cm = self.cell.start_trace_template.get_default_view(CircuitModelView)
            tte_cm = self.cell.start_trace_template.get_default_view(CircuitModelView)

            trans_lv = self.cell.get_default_view(LayoutView)
            n_modes = len(tts_cm.n_eff_values)
            neffs = np.array([[0.5 * np.array(tts_cm.get_n_eff(Environment(wavelength=wl), mode=mode)) +
                               0.5 * np.array(tte_cm.get_n_eff(Environment(wavelength=wl), mode=mode))
                               for mode in range(n_modes)]
                              for wl in tts_cm.wavelengths])

            phase_error = np.array([0.5 * (tts_cm.get_phase_error(mode=mode) + tte_cm.get_phase_error(mode=mode))
                                    for mode in range(n_modes)])

            model_class = generate_wg_model(n_modes=len(tte_cm.n_eff_values))
            return model_class(length=trans_lv.length,  # calculated from the layout automatically
                               n_effs=neffs,
                               wavelengths=tts_cm.wavelengths,
                               phase_error=phase_error)
