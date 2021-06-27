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
import collections
from ipkiss3.pcell.layout.netlist_extraction.netlist_extraction import extract_unconnected_ports
from ipkiss3.pcell.netlist.instance import InstanceTerm
import warnings
from .utils import get_port_from_interface, multiple_entries
from .connector_functions import manhattan


def get_child_instances(child_cells, joins=[], place_specs=[], verify=True):
    """Returns a dictionary of instances based on child_cells, joins and place_specs.
    Parameters
    ----------
    joins : list of tuples
    place_specs : dict
    child_cells : dict
    Returns
    -------
    insts : i3.InstanceDict
        Dictionary of child_cells, joins and place_specs
    """

    insts = i3.InstanceDict([
        (instname, i3.SRef(cell, name=instname))
        for instname, cell in child_cells.items()
    ])

    joins_spec = [i3.Join(join[0], join[1]) for join in joins]

    insts = i3.place_insts(insts,
                           specs=place_specs + joins_spec,
                           verify=verify)
    return insts


def get_connector_instances(instances, connectors, name, default_connector_function=manhattan):
    """Returns a dictionary of connector instances.
    Parameters
    ----------
    instances : dict
        Placed instances
    connectors : list
        List of connectors
    name : str
        Name of the parent cell - all the connectors will be prepended with that name
    default_connector_function : connector function, optional
    Return
    -------
    connector_instances : i3.InstanceDict()
        Dictionary of connector instances
    """
    connector_instances = i3.InstanceDict()
    for cnt, c in enumerate(connectors):
        start_port = get_port_from_interface(port_id=c[0], inst_dict=instances)
        end_port = get_port_from_interface(port_id=c[1], inst_dict=instances)
        connector_function = default_connector_function
        if len(c) > 2:
            if c[2] is not None:
                connector_function = c[2]
        kwargs = {}
        if len(c) == 4:
            if c[3] is not None:
                kwargs = c[3]

        c_cell_name = name + "_connector{}".format(cnt)

        try:
            kwargs.update({"start_port": start_port,
                           "end_port": end_port,
                           "name": c_cell_name})

            cell = connector_function(**kwargs)
            cell.get_default_view(i3.LayoutView).layout
        except Exception as exp:
            if hasattr(connector_function, __name__):
                c_name = connector_function.__name__
            else:
                c_name = str(connector_function)

            c_title = "({},{},{})".format(c[0], c[1], c_name)
            print
            msg = """
        Connector Error {} - using adding an element instead:
        - start_port: {}
        - end_port: {}
        - connector_function: {}
        - connector_function_error: {}
        """.format(c_title, start_port.position, end_port.position, c_name, exp)
            warnings.warn(msg)
            cell = i3.LayoutCell(name=c_cell_name+"_error")
            if hasattr(i3.TECH.PPLAYER, "ERROR"):
                err_layer = i3.TECH.PPLAYER.ERROR.GENERIC
            else:
                err_layer = i3.TECH.PPLAYER.NONE
            err_el = i3.Path(shape=[start_port.position, end_port.position],
                             layer=err_layer)

            cell.Layout(elements=[err_el])

        connector_instances += i3.SRef(name=c_cell_name, reference=cell)
    return connector_instances


class CircuitCell(i3.PCell):
    child_cells = i3.DefinitionProperty(
        doc="dict to create the instances of the child cells. Format is {'inst_name1': PCell}")
    connectors = i3.ListProperty(
        doc="list of tuples connecting the instances. Format is"
            " [('inst1:term1','inst2:term2',connector_function,kwargs), ...]",
        restriction=i3.RestrictTypeList(allowed_types=[collections.Sequence]))
    joins = i3.ListProperty(doc="List of tuples connecting instances through joins,"
                                "together with the connectors they define"
                                "the entire connectivity of the circuit.")
    place_specs = i3.ListProperty(doc="List of placement place_specs")
    propagated_electrical_ports = i3.ListProperty(doc="List of electrical ports that are propagated to the next level. "
                                                      "By default None are propagated")
    external_port_names = i3.DefinitionProperty(
        doc="Map of the free instance terms/ports to the names of external terms/ports. "
            "Format is a dict {'inst:term' : 'new_term_name'}."
            "If a term/port is not listed, the format `instname_portname` will be used",
        restriction=i3.RestrictDictValueType(str))
    verify = i3.BoolProperty(default=True, doc="Verify the validity of the connectors, joins and place_specs")
    default_connector_function = i3.CallableProperty(default=manhattan)

    def validate_properties(self):
        joins = self.joins
        connectors = self.connectors
        connectivity_tuples = joins + connectors
        connectivity_ports = [el[0] for el in connectivity_tuples] + [el[1] for el in connectivity_tuples]
        non_unique_ports = multiple_entries(connectivity_ports)

        if len(non_unique_ports) > 0:
            error_cause = "The following ports appear multiple times" \
                          " in connectors and joins {}".format(non_unique_ports)
            raise i3.PropertyValidationError(error_class_instance=self,
                                             error_cause=error_cause,
                                             error_var_values={"connectors": self.connectors,
                                                               "joins": self.joins})
        return True

    def _default_propagated_electrical_ports(self):
        return []

    def _default_connectors(self):
        return []

    def _default_joins(self):
        return []

    def _default_external_port_names(self):
        return {}

    def _default_child_cells(self):
        return dict()

    def _default_place_specs(self):
        return []

    @i3.cache()
    def get_child_instances(self):
        return get_child_instances(child_cells=self.child_cells,
                                   joins=self.joins,
                                   place_specs=self.place_specs,
                                   verify=self.verify)

    def get_connector_instances(self):
        return get_connector_instances(instances=self.get_child_instances(),
                                       connectors=self.connectors,
                                       name=self.name,
                                       default_connector_function=self.default_connector_function)

    class Layout(i3.LayoutView):

        def _generate_instances(self, insts):
            insts += self.cell.get_child_instances()
            insts += self.cell.get_connector_instances()
            return insts

        def _generate_elements(self, elems):
            return elems

        def _generate_ports(self, ports):
            insts = self.instances
            labels = extract_unconnected_ports(insts)
            for insts_name, port in labels:
                label = "{}:{}".format(insts_name, port.name)
                if label in self.external_port_names:
                    name = self.external_port_names[label]
                else:
                    name = "{}_{}".format(insts_name, port.name)
                new_port = port.modified_copy(name=name)
                if new_port.domain == i3.OpticalDomain:
                    ports += new_port
                else:
                    if new_port.name in self.propagated_electrical_ports:
                        ports += new_port

            return ports

    class Netlist(i3.NetlistFromLayout):

        def _generate_netlist(self, netlist):
            netlist = super(CircuitCell.Netlist, self)._generate_netlist(self)
            for i in netlist.instances.itervalues():
                for t in i.terms.itervalues():
                    if t.domain == i3.ElectricalDomain:
                        term_name = "{}_{}".format(i.name, t.name)
                        label = "{}:{}".format(i.name, t.name)
                        term_mapped_name = term_name
                        if label in self.external_port_names:
                            term_mapped_name = self.external_port_names[label]
                        netlist.link('{}'.format(term_mapped_name), '{}:{}'.format(i.name, label.split(':')[1]))

            for net in netlist.get_nets_to_terms():
                if net.domain == i3.OpticalDomain:
                    terms = net.terms
                    for idx, term in enumerate(terms):
                        if isinstance(term, InstanceTerm):
                            terms[1 - idx].n_modes = term.term.n_modes
            return netlist

    class CircuitModel(i3.CircuitModelView):
        def _generate_model(self):
            return i3.HierarchicalModel.from_netlistview(self.netlist_view)
