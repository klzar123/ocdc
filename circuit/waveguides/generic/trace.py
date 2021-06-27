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

from ipkiss3.pcell.netlist import NetlistView
from ipcore.properties.predefined import PositiveNumberProperty, NonNegativeNumberProperty
from ipcore.properties.predefined import NumpyArrayProperty, ListProperty
from ipkiss3.pcell.photonics.waveguide import WindowWaveguideTemplate, TemplatedWindowWaveguide
from ipkiss3.pcell.layout.view import LayoutView
from ipkiss3.simulation.engines.caphe_circuit_sim.pcell_views.caphemodel import CircuitModelView
from ipkiss3.pcell.trace.window.window import PathTraceWindow
from ipkiss3.pcell.cell.template import _ViewTemplate
from ipkiss3.pcell.cell.view import ViewInSameCellProperty
from ipkiss3.pcell.model import CompactModel
from ipkiss3.pcell.photonics.term import OpticalTerm
from ipkiss.technology import get_technology
from pysics.optics.environment import Environment
import numpy as np
from scipy.interpolate import RectBivariateSpline
from ipcore.properties.descriptor import LockedProperty

TECH = get_technology()


def generate_wg_model(n_modes=1):

    class WGBroadBandPhaseErrorCompactModel(CompactModel):
        """Broadband higher order waveguide model that interpolates the effective index across wavelengths.

        Parameters
        ----------
        n_effs : array of effective indeces
        wavelengths : array of wavelengths at which n_eff is defined [um]
        length : optical length of the waveguide [um]
        phase_error : phase error accumulated per unit of optical length 1/sqrt [um]
        """
        parameters = [
            'n_effs',
            'wavelengths',
            'length',
            'phase_error'
        ]
        _model_type = "python"
        terms = [OpticalTerm(name='in', n_modes=n_modes), OpticalTerm(name='out', n_modes=n_modes)]

        def calculate_smatrix(parameters, env, S):
            for cnt in range(n_modes):
                n_effs = parameters.n_effs[:, cnt]
                phase_error = parameters.phase_error[cnt]
                neff_total = (np.interp(env.wavelength, parameters.wavelengths, np.real(n_effs)) +
                              1j * np.interp(env.wavelength, parameters.wavelengths, np.imag(n_effs)))
                beta = 2 * np.pi / env.wavelength * neff_total
                in_p = "in:" + str(cnt)
                out_p = "out:" + str(cnt)
                S[in_p, out_p] = S[out_p, in_p] = np.exp(1j * (beta * parameters.length +
                                                               phase_error * np.sqrt(parameters.length)))

    return WGBroadBandPhaseErrorCompactModel


class GenericWaveguide(TemplatedWindowWaveguide):

    class Netlist(NetlistView):
        def _generate_terms(self, terms):
            n_modes = len(self.template.cell.get_default_view(CircuitModelView).n_eff_values)
            terms += OpticalTerm(name="in", n_modes=n_modes)
            terms += OpticalTerm(name="out", n_modes=n_modes)
            return terms

    class CircuitModel(TemplatedWindowWaveguide.CircuitModel):

        def _generate_model(self):
            template = self.template
            wavelengths = self.template.wavelengths
            n_modes = len(template.n_eff_values)
            neffs = np.array([
                [template.get_complex_n_eff(Environment(wavelength=wl), mode=mode) for mode in range(n_modes)]
                for wl in wavelengths
            ])
            phase_error = np.array([template.get_phase_error(mode=mode) for mode in range(n_modes)])
            model_class = generate_wg_model(n_modes=n_modes)
            return model_class(length=self.length,  # calculated from the layout automatically
                               n_effs=neffs,
                               wavelengths=wavelengths,
                               phase_error=phase_error)


class GenericWaveguideTemplate(WindowWaveguideTemplate):
    _templated_class = GenericWaveguide

    class Layout(WindowWaveguideTemplate.Layout):

        core_process = LockedProperty(doc="For Backward compatibility - everything is set through the layers")
        cladding_process = LockedProperty(doc="For Backward compatibility - everything is set through the layers")
        core_purpose = LockedProperty(doc="For Backward compatibility - everything is set through the layers")
        cladding_purpose = LockedProperty(doc="For Backward compatibility - everything is set through the layers")

        def _default_core_layer(self):
            return TECH.PPLAYER.SI

        def _default_core_width(self):
            return 0.5

        def _default_windows(self):
            windows = [PathTraceWindow(layer=self.core_layer,
                                       start_offset=-0.5 * self.core_width,
                                       end_offset=0.5 * self.core_width)]
            return windows

        def _default_core_process(self):
            return self.core_layer.process

        def _default_core_purpose(self):
            return self.core_layer.purpose

        def _default_cladding_process(self):
            return self.cladding_layer.process

        def _default_cladding_purpose(self):
            return self.cladding_layer.purpose

    class CircuitModel(CircuitModelView, _ViewTemplate):

        phase_error_correlation_length = NonNegativeNumberProperty(
            doc="Correlation length (in um) of the sidewall roughness")
        phase_error_width_deviation = NonNegativeNumberProperty(
            doc="Standard deviation (amplitude) of the sidewall roughness")
        wavelengths = NumpyArrayProperty(doc="Wavelength points for interpolation.")
        widths = NumpyArrayProperty(doc="Widths points for the interpolation.")
        n_eff_values = ListProperty(doc="List of 2D array of complex refractive"
                                        "index as a function of wavelength and width."
                                        "The first dimension in the wavelength the second one "
                                        "is the width, one for each supported mode")
        center_wavelength = PositiveNumberProperty(
            doc="Center wavelength of the waveguide which is used for calculations of n_g,"
                " loss_dbm or n_eff when no wavelength is specified")
        layout_view = ViewInSameCellProperty(LayoutView)

        def _default_phase_error_width_deviation(self):
            return 0.0

        def _default_phase_error_correlation_length(self):
            return 0.0

        def _default_center_wavelength(self):
            return (max(self.wavelengths) + min(self.wavelengths)) / 2.0

        def _default_n_eff_values(self):
            """n_eff_values as a 2D array, as function of wavelength and width.

            n_eff_values is a MxN array, where M (rows) is the number of wavelength points,
            and N (cols) is the number of widths.

            Examples
            --------
            n_eff_values = [np.array([[2.24378704, 2.53735656, 2.66001948, 2.71562179, 2.75466422, 2.77430224],
                                     [2.2091054, 2.51351447, 2.64091618, 2.69873319, 2.7392829, 2.7597774],
                                     [2.17442376, 2.48967238, 2.62181287, 2.68184458, 2.72390157, 2.74525256],
                                     [2.13974212, 2.46583029, 2.60270956, 2.66495597, 2.70852025, 2.73072772],
                                     [2.10506048, 2.44198821, 2.58360625, 2.64806737, 2.69313892, 2.71620288]])]
            n_eff_values = n_eff_values + 0.001 * 1j  # Adding some loss. Here non disperisve material loss.
            return n_eff_values
            """
            raise NotImplementedError("Please define parameter n_eff_values for your waveguide template.")

        def _default_wavelengths(self):
            """Default list of wavelengths.

            See also
            --------
            n_eff_values

            Examples
            --------
            return np.linspace(1.5, 1.6, 5)
            """
            raise NotImplementedError("Please define parameter wavelengths for your waveguide template.")

        def _default_widths(self):
            """Default list of widths.

            See also
            --------
            n_eff_values

            Examples
            --------
            return np.linspace(0.4, 1.2, 6)
            """
            raise NotImplementedError("Please define parameter widths for your waveguide template.")

        def _get_n_eff_interps(self):
            r = [RectBivariateSpline(self.wavelengths,
                                     self.widths,
                                     np.real(n_eff),
                                     bbox=[self.wavelengths[0] * 0.9, self.wavelengths[-1] * 1.1, self.widths[0] * 0.9,
                                           self.widths[-1] * 1.1]) for n_eff in self.n_eff_values]

            c = [RectBivariateSpline(self.wavelengths,
                                     self.widths,
                                     np.imag(n_eff),
                                     bbox=[self.wavelengths[0] * 0.9, self.wavelengths[-1] * 1.1, self.widths[0] * 0.9,
                                           self.widths[-1] * 1.1]) for n_eff in self.n_eff_values]

            return r, c

        def _get_n_eff_for_wavelength_and_width(self, wavelength, width, mode=0):
            rs, cs = self._get_n_eff_interps()
            n_effs = [float(r(wavelength, width)) + 1j * float(c(wavelength, width)) for r, c in zip(rs, cs)]
            return n_effs[mode]

        def _get_dndw(self, eps=1e-6, mode=0):
            """The change in index as function of width for the center wavelength."""
            wl = self.center_wavelength
            width = self.layout_view.core_width
            w1 = width - eps
            w2 = width + eps

            n1 = np.real(self._get_n_eff_for_wavelength_and_width(wl, w1, mode=mode))
            n2 = np.real(self._get_n_eff_for_wavelength_and_width(wl, w2, mode=mode))

            return (n2 - n1) / (w2 - w1)

        def get_phase_error(self, mode=0):
            """Returns sigma(phase error)/sqrt(um), sigma_dw given in nm at the center wavelength."""
            if self.phase_error_width_deviation > 0 and self.phase_error_correlation_length > 0:
                dbeta_dw = 2 * np.pi * self._get_dndw(mode=mode) / self.center_wavelength
                sigma_pe = np.sqrt(2 * self.phase_error_correlation_length * (dbeta_dw ** 2)
                                   * (self.phase_error_width_deviation ** 2))
                return np.random.normal(0.0, sigma_pe)
            else:
                return 0.0

        def get_n_g(self, environment=None, mode=0):
            """Returns the actual group index of the waveguide cross section for all the parameters in the Environment
            (e.g. wavelength, temperature).
            Use this method to retrieve the group index, rather than the property 'n_g'.
            """
            wavelength = environment.wavelength if environment is not None else self.center_wavelength
            dwav = 0.001
            w1 = wavelength + dwav / 2.0
            w2 = wavelength - dwav / 2.0
            width = self.layout_view.core_width
            n1 = np.real(self._get_n_eff_for_wavelength_and_width(w1, width, mode=mode))
            n2 = np.real(self._get_n_eff_for_wavelength_and_width(w2, width, mode=mode))

            ng = (w2 * n1 - w1 * n2) / (w2 - w1)

            return ng

        def get_loss_dB_m(self, environment=None, mode=0):
            """Returns the propagation loss of the waeguide cross section for all the parameters in the Environment
            (e.g. wavelength, temperature).
            Use this method to retrieve the loss, rather than the property 'loss_dB_m'.
            """
            wavelength = environment.wavelength if environment is not None else self.center_wavelength
            width = self.layout_view.core_width
            n1 = self._get_n_eff_for_wavelength_and_width(wavelength, width, mode=mode)

            trans_1m = np.exp(2 * np.pi * -np.imag(n1) * 1e6 / wavelength)
            db_1m = 20.0 * np.log10(trans_1m)
            return db_1m

        def get_complex_n_eff(self, environment=None, mode=0):
            """Returns the complex part of the effective index.
            """
            if environment is None:
                wavelength = self.center_wavelength
            else:
                wavelength = environment.wavelength

            width = self.cell.get_default_view(LayoutView).core_width
            n1 = self._get_n_eff_for_wavelength_and_width(wavelength, width, mode=mode)
            return n1

        def get_n_eff(self, environment=None, mode=0):
            return np.real(self.get_complex_n_eff(environment=environment, mode=mode))

    class Netlist(WindowWaveguideTemplate.Netlist):

        def _default__term_type(self):
            class CustomTerm(OpticalTerm):
                def _default_n_modes(self2):
                    return len(self.cell.get_default_view(CircuitModelView).n_eff_values)
            return CustomTerm
