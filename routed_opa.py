from si_fab import all as pdk
from pteam_library_si_fab import all as pt_lib
from circuit.circuitcell import CircuitCell, get_port_from_interface
from circuit.connector_functions import manhattan
from ipkiss3 import all as i3
import re
from OPA import OPA

class RoutedOPA(CircuitCell):
    """Optical phased array (OPA) whose heaters are electrically connected to metal contact pads via electrical wires.
    In this example, the device under test (DUT) is the OPA, but the code has been written in such a way that
    it can be generalised to other PCells with electrical ports.
    """
    dut = i3.ChildCellProperty(doc="The device under test, in this case the OPA")
    electrical_links = i3.LockedProperty(doc="The electrical connectors between the heaters and the contact pads")
    bond_pads_spacing = i3.PositiveNumberProperty(default=100.0, doc="The horizontal distance between the contact pads")
    wire_spacing = i3.PositiveNumberProperty(default=10.0, doc="The spacing between the electrical wires")

    def _default_dut(self):
        return OPA()

    def _default_connectors(self):
        # Default optical connectors (don't put electrical connectors here)
        # Connect input and output optical ports of the DUT to grating couplers

        dut_lv = self.dut.get_default_view(i3.LayoutView)

        # List of output optical ports of the dut
        port_list_out_sorted = [p.name for p in dut_lv.ports.y_sorted() if re.search("(out)", p.name)]

        # Connect them all to output grating couplers
        conn = [("dut:{}".format(p), "gr{}:out".format(p), manhattan) for p in port_list_out_sorted]

        # Connect the input grating coupler
        conn.append(("dut:in", "gr_in:out", manhattan))

        return conn

    def _default_electrical_links(self):
        # Default electrical connectors
        conn = []
        dut_lv = self.dut.get_default_view(i3.LayoutView)

        # List of input and list of output electrical ports of the DUT
        el_in_sorted = [p.name for p in dut_lv.ports.y_sorted() if re.search("(hti)", p.name)]
        el_out_sorted = [p.name for p in dut_lv.ports.y_sorted_backward() if re.search("(hto)", p.name)]

        # Connect them all to the contact pads.
        conn.extend([("dut:{}".format(p), "bp{}:m1".format(p)) for p in el_in_sorted])
        conn.extend([("dut:{}".format(p), "bp{}:m1".format(p)) for p in el_out_sorted])

        return conn

    def _default_child_cells(self):
        # The child cells are the DUT, the grating couplers and the contact pads
        child_cells = {"dut": self.dut}
        for connector in self.connectors:
            out_cell = connector[1].split(":")[0]
            child_cells[out_cell] = pdk.FC_TE_1550()
        for el_link in self.electrical_links:
            out_cell = el_link[1].split(":")[0]
            child_cells[out_cell] = pdk.BONDPAD_5050()

        return child_cells

    def _default_place_specs(self):
        specs = []

        # Define the positions of the ports.
        bp_cnt = 0
        bp_spacing = self.bond_pads_spacing
        height = self.dut.get_default_view(i3.LayoutView).size_info().north

        # Place the dut (splitter tree) at the origin
        specs.append(i3.Place("dut", (0, 0)))

        # Place the outputs and inputs of the optical connectors in respect to each other
        for connector in self.connectors:
            if "in" in connector[0]:
                specs.append(i3.PlaceRelative(connector[1], connector[0], (-100, 0), angle=0.0))
            else:
                specs.append(i3.PlaceRelative(connector[1], connector[0], (300, 0), angle=180.0))

        # Do the same for the electrical connectors
        for el_link in self.electrical_links:
            specs.append(
                i3.Place(
                    el_link[1].split(":")[0],
                    (bp_cnt * bp_spacing, height + bp_spacing + len(self.electrical_links) * self.wire_spacing)
                )
            )
            bp_cnt = bp_cnt + 1
        return specs

    def _default_external_port_names(self):
        epn = dict()
        epn["gr_in:vertical_in"] = "in"
        for cnt in range(self.dut._get_n_outputs()):
            epn["grout{}:vertical_in".format(cnt)] = "out{}".format(cnt)
        return epn

    class Layout(CircuitCell.Layout):
        def _generate_elements(self, elems):
            n_links = len(self.electrical_links)
            cnt = 0
            cnt_x = 0
            insts = self.instances

            # Loop over each electrical link to provide the route for them
            for el_link in self.electrical_links:
                sp = get_port_from_interface(port_id=el_link[0], inst_dict=insts)  # Start port
                ep = get_port_from_interface(port_id=el_link[1], inst_dict=insts)  # End port
                d = self.wire_spacing
                cnt_x = cnt_x + 1
                if sp.x > ep.x:
                    cnt = cnt + 1
                else:
                    cnt = cnt - 1
                shape = i3.Shape([
                    sp,
                    (sp.x - (n_links/2 - cnt_x) * d, sp.y),
                    (sp.x - (n_links/2 - cnt_x) * d, ep.y - self.bond_pads_spacing + cnt * d),
                    (ep.x, ep.y - self.bond_pads_spacing + cnt * d),
                    ep
                ])

                # Draw a path along the shape defined above on the M1 metal layer
                elems += i3.Path(shape=shape, layer=i3.TECH.PPLAYER.M1, line_width=4.0)

            return elems

    class Netlist(CircuitCell.Netlist):
        def _generate_netlist(self, netlist):
            netlist = super(CircuitCell.Netlist, self)._generate_netlist(self)  # Optical netlist

            for p1, p2 in self.electrical_links:
                term_name = p1.split(":")[1]
                netlist += i3.ElectricalTerm(name=term_name)  # Adding an output term
                del (netlist.instances["bp{}".format(term_name)])  # Deleting the bondpads from the netlist
                netlist.link("dut:{}".format(term_name), term_name)  # Linking the dut to the bondpads

            return netlist

if __name__ == "__main__":
    # Heater
    heater = pdk.HeatedWaveguide(name="heated_wav")
    heater.Layout(shape=[(0, 0), (1000.0, 0.0)])

    # Unrouted OPA
    opa = OPA(name="opa_array", heater=heater, levels=3)

    # Routed OPA
    opa_routed = RoutedOPA(dut=opa)
    opa_routed.Layout().visualize()