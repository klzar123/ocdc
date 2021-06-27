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

from crossing.crossing_utils import TraceChainWithCenterLine
from ipkiss3 import all as i3


def combine_connectors(connector_functions=[], transformations=[]):
    """Creates a new connector that combines several connectors by placing them back-to-back. The transformations list
    denotes the transformations of the intermediary ports in absolute coordinates.

    Parameters
    ----------
    connector_functions : list of connector functions
        List of connector functions that you want aggregate
    transformations : list of transformations
        List transformations for the intermediate points in absolute coordinates

    Return
    -------
    new_connector : connector function
        New connector function. Shape and connector_kwargs are unused in the new function.

    Examples
    ---------
    from si_fab import all as pdk
    from ipkiss3 import all as i3
    from circuit.circuit_functions import bezier_sbend
    from circuit.combine_connectors import combine_connectors

    # Instantiate trace templates to use for the ports
    tt1 = pdk.SiWireWaveguideTemplate()
    tt1.Layout(core_width=0.5)

    port1 = i3.OpticalPort(position=(0.0, 0.0), angle=0.0, trace_template=tt1)
    port2 = i3.OpticalPort(position=(60.0, 60.0), angle=180.0, trace_template=tt1)

    new_connector = combine_connectors(connector_functions=[bezier_sbend, bezier_sbend],
                                       transformations=[(30, 30,0)]
                                       )

    cell = new_connector(start_port=port1, end_port=port2, name="double_sbend")
    lv = cell.get_default_view(i3.LayoutView)
    lv.visualize()
    """

    if len(connector_functions) != len(transformations) + 1:
        raise Exception(
            "The length of the transformation array need to be equal to the length of the circuit functions - 1")

    cleaned_transformations = []
    for t in transformations:
        if isinstance(t, tuple):
            if len(t) == 2:
                cleaned_transformations.append((i3.Translation(t)))
            else:
                trans = i3.Translation(translation=(t[0], t[1]))
                cleaned_transformations.append(i3.Rotation(rotation=t[2]) + trans)
        else:
            cleaned_transformations.append(t)

    def new_connector(start_port, end_port, name=None, **kwargs):

        start_ports = [start_port] + [i3.OpticalPort(trace_template=start_port.trace_template,
                                                     position=(0.0, 0.0)).transform(transformation=t)
                                      for t in cleaned_transformations]

        end_ports = [p.modified_copy(angle=p.angle + 180.0)
                     for p in start_ports[1:]] + [end_port]

        traces = []
        for cnt, (cf, sp, ep) in enumerate(zip(connector_functions, start_ports, end_ports)):
            seg_name = "{}_segment_{}".format(name, cnt)
            traces.append(cf(start_port=sp, end_port=ep, name=seg_name, **kwargs))

        return TraceChainWithCenterLine(name=name, traces=traces)

    return new_connector
