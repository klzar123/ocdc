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

from ipkiss3.pcell.model import CompactModel
from ipkiss3.pcell.photonics.term import OpticalTerm
from ipkiss3.pcell.wiring import ElectricalTerm
from numpy import pi, exp, interp, real, imag, sqrt, abs


class HeaterBroadBandPhaseErrorCompactModel(CompactModel):
    """
    Broadband higher order waveguide model that interpolates the effective index across wavelengths,
    while allowing for modulation as a function of the difference between two electrical signals.
    The modulation efficiency is coupled to the provided VpiLpi and is instantaneous.

    Parameters
    ----------
    n_effs :
        Array of effective indices.
    wavelengths :
        Array of wavelengths at which n_eff is defined [um].
    length : float
        Optical length of the waveguide [um].
    width: float
        Total width of the heater [um]
    phase_error : float
        Phase error accumulated per unit of optical length 1/sqrt [um].
    p_pi_sq : float
        Power required to obtain a pi phaseshift on a square with unit sheet resistance (1 Ohm/sq) [W.Ohm].
    """

    parameters = [
        'n_effs',
        'wavelengths',
        'length',
        'width',
        'phase_error',
        'p_pi_sq',
    ]

    terms = [OpticalTerm(name='in'),
             OpticalTerm(name='out'),
             ElectricalTerm(name="elec1"),
             ElectricalTerm(name="elec2")]

    def calculate_smatrix(parameters, env, S):
        neff_total = interp(
            env.wavelength,
            parameters.wavelengths,
            real(parameters.n_effs)
        ) + 1j * interp(
            env.wavelength,
            parameters.wavelengths,
            imag(parameters.n_effs)
        )

        beta = 2 * pi / env.wavelength * neff_total
        tot_phase = beta * parameters.length + parameters.phase_error * sqrt(parameters.length)

        S['in', 'out'] = S['out', 'in'] = exp(1j * tot_phase)

    def calculate_signals(parameters, env, output_signals, y, t, input_signals):
        v_diff = abs(input_signals['elec2'] - input_signals['elec1'])
        neff_total = interp(
            env.wavelength,
            parameters.wavelengths,
            real(parameters.n_effs)
        ) + 1j * interp(
            env.wavelength,
            parameters.wavelengths,
            imag(parameters.n_effs)
        )
        beta = 2 * pi / env.wavelength * neff_total
        ratio = parameters.length / parameters.width
        phase_mod = pi * (v_diff ** 2) / (parameters.p_pi_sq * ratio)
        tot_phase = beta * parameters.length + parameters.phase_error * sqrt(parameters.length) + phase_mod
        transmission = exp(1j * tot_phase)
        output_signals['in'] = transmission * input_signals['out']
        output_signals['out'] = transmission * input_signals['in']


class PhaseShifterBroadBandPhaseErrorTauCompactModel(HeaterBroadBandPhaseErrorCompactModel):
    """ Broadband higher order waveguide model that interpolates the effective index across wavelengths,
    while allowing for modulation as a function of a difference between two electrical signals.
    The modulation efficiency is coupled to the specified VpiLpi and to the time constant tau.
    Parameters
    ----------
    n_effs :
        Array of effective indices.
    wavelengths :
        Array of wavelengths at which n_eff is defined [um].
    length : float
        Optical length of the waveguide [um].
    phase_error : float
        Phase error accumulated per unit of optical length 1/sqrt [um].
    vpi_lpi : float
        VpiLpi of the phase modulation in [V.cm].
    tau: float
        Time constant of the exponential response of the modulator effect [s].
    """

    parameters = [
        'n_effs',
        'wavelengths',
        'length',
        'phase_error',
        'vpi_lpi',
        'tau'
    ]

    states = ['Vd']

    terms = [OpticalTerm(name='in'),
             OpticalTerm(name='out'),
             ElectricalTerm(name="anode"),
             ElectricalTerm(name="cathode")]

    def calculate_dydt(parameters, env, dydt, y, t, input_signals):
        v = input_signals['cathode'] - input_signals['anode']
        tau = max(parameters.tau, 1e-15)
        dydt['Vd'] = (v - y["Vd"]) / tau

    def calculate_signals(parameters, env, output_signals, y, t, input_signals):
        neff_total = (interp(env.wavelength, parameters.wavelengths, real(parameters.n_effs)) +
                      1j * interp(env.wavelength, parameters.wavelengths, imag(parameters.n_effs)))

        beta = 2 * pi / env.wavelength * neff_total
        length_cm = parameters.length * 1e-4
        phase_mod = pi * (y['Vd'] * length_cm) / parameters.vpi_lpi
        tot_phase = beta * parameters.length + parameters.phase_error * sqrt(parameters.length) + phase_mod
        transmission = exp(1j * tot_phase)
        output_signals['in'] = transmission * input_signals['out']
        output_signals['out'] = transmission * input_signals['in']
