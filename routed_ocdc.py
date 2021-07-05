from ipkiss3 import all as i3
from circuit.all import CircuitCell, manhattan
from circuit.utils import get_port_from_interface
from CSiP180Al import all as pdk
from ocdc import OCDC
from bond_pad import BondPad
import re


def take_mzi_num(p):
    return int(re.findall(r"\d+", p)[1])


def take_mzis_mzi_num(p):
    return (int(re.findall(r"\d+", p)[1]), -int(re.findall(r"\d+", p)[0]), -int(re.findall(r"\d+", p)[2]))


def take_mzis_mzi_num2(p):
    return (int(re.findall(r"\d+", p)[1]), int(re.findall(r"\d+", p)[0]), int(re.findall(r"\d+", p)[2]))


def merge_connector(ELEC1, ELEC2):
    conn = []
    for i in range(len(ELEC1)):
        elec1 = ELEC1[i]
        elec2 = ELEC2[i]
        conn.append(("dut:{}".format(elec1), "bp_{}:m1".format(elec1)))
        conn.append(("dut:{}".format(elec2), "bp_{}:m1".format(elec2)))
    return conn


class RoutedOCDC(CircuitCell):
    _name_prefix = "Routed_OCDC"
    dut = i3.ChildCellProperty(doc="OCDC")
    electrical_links = i3.LockedProperty(doc="The electrical connectors between the heaters and the contact pads")
    bond_pads_spacing = i3.PositiveNumberProperty(default=50.0, doc="The horizontal distance between the contact pads")
    wire_spacing = i3.PositiveNumberProperty(default=10.0, doc="The spacing between the electrical wires")

    def _default_dut(self):
        return OCDC()

    def _default_connectors(self):
        # Default optical connectors (don't put electrical connectors here)
        # Connect input and output optical ports of the DUT to grating couplers
        conn = [("gr_in:wg", "dut:in", manhattan), ("dut:out", "gr_out:wg", manhattan)]
        return conn

    def _default_electrical_links(self):
        conn = []
        dut_lv = self.dut.get_default_view(i3.LayoutView)
        # List of input and list of output electrical ports of the DUT
        n_rows = self.dut.get_n_rows()
        mzi_nums = self.dut.get_mzi_nums()
        up_mzi_elec1 = []
        down_mzi_elec1 = []
        up_mzi_elec2 = []
        down_mzi_elec2 = []
        for i in range(mzi_nums):
            for p in dut_lv.ports:
                if re.search("(mzi)", p.name) and re.search("(elec1)", p.name) and int(
                        re.findall(r"\d+", p.name)[1]) == i:
                    if int(re.findall(r"\d+", p.name)[0]) >= n_rows / 2:
                        up_mzi_elec1.append(p.name)
                    else:
                        down_mzi_elec1.append(p.name)
                elif re.search("(mzi)", p.name) and re.search("(elec2)", p.name) and int(
                        re.findall(r"\d+", p.name)[1]) == i:
                    if int(re.findall(r"\d+", p.name)[0]) >= n_rows / 2:
                        up_mzi_elec2.append(p.name)
                    else:
                        down_mzi_elec2.append(p.name)

        up_mzi_elec1.sort(key=take_mzis_mzi_num2)
        down_mzi_elec1.sort(key=take_mzis_mzi_num)
        up_mzi_elec2.sort(key=take_mzis_mzi_num2)
        down_mzi_elec2.sort(key=take_mzis_mzi_num)

        # heater
        ht_elec1 = [p.name for p in dut_lv.ports.y_sorted() if
                    re.search("(ht)", p.name) and re.search("(elec1)", p.name)]
        ht_elec2 = [p.name for p in dut_lv.ports.y_sorted() if
                    re.search("(ht)", p.name) and re.search("(elec2)", p.name)]
        up_ht_elec1 = ht_elec1[len(ht_elec1) / 2:]
        up_ht_elec2 = ht_elec2[len(ht_elec2) / 2:]

        down_ht_elec1 = ht_elec1[:len(ht_elec1) / 2]
        down_ht_elec2 = ht_elec2[:len(ht_elec2) / 2]
        down_ht_elec1.reverse()
        down_ht_elec2.reverse()

        # Connect them all to the contact pads.
        conn.extend(merge_connector(up_mzi_elec1, up_mzi_elec2))
        conn.extend(merge_connector(up_ht_elec1, up_ht_elec2))
        conn.extend(merge_connector(down_mzi_elec1, down_mzi_elec2))
        conn.extend(merge_connector(down_ht_elec1, down_ht_elec2))

        return conn

    def _default_child_cells(self):
        # The child cells are the DUT, the grating couplers and the contact pads
        child_cells = dict()
        child_cells["dut"] = self.dut
        child_cells["gr_in"] = pdk.GC_TE_1550()
        child_cells["gr_out"] = pdk.GC_TE_1550()
        for el_link in self.electrical_links:
            out_cell = el_link[1].split(":")[0]
            child_cells[out_cell] = BondPad()
        return child_cells

    def _default_place_specs(self):
        specs = []

        # Define the positions of the ports.
        bp_cnt_u = 0
        bp_cnt_d = 0
        bp_spacing = self.bond_pads_spacing
        height = - self.dut.get_default_view(i3.LayoutView).size_info().north / 2

        # Place the dut (splitter tree) at the origin
        specs.append(i3.Place("dut", (0, 0)))

        # Place the optical connectors
        specs.append(i3.Place("gr_in", (-100, 0)))
        specs.append(i3.Place("gr_out", (self.dut.get_default_view(i3.LayoutView).size_info().east + 100, 0)))
        specs.append(i3.FlipH("gr_out"))

        # Place the Bondpads
        for el_link in self.electrical_links:
            bp_name = el_link[1].split(":")[0]
            row_num = int(re.findall(r"\d+", bp_name)[0])
            if row_num >= self.dut.get_n_rows() / 2:
                if re.search("elec1", bp_name):
                    specs.append(
                        i3.Place(
                            bp_name,
                            (bp_cnt_u * bp_spacing,
                             height + bp_spacing + len(self.electrical_links) * self.wire_spacing)
                        )
                    )
                else:
                    specs.append(
                        i3.Place(
                            bp_name,
                            (bp_cnt_u * bp_spacing - 3.5 * bp_spacing / 2,
                             height + bp_spacing + len(self.electrical_links) * self.wire_spacing + 127)
                        )
                    )
                bp_cnt_u = bp_cnt_u + 1
            else:
                if re.search("elec1", bp_name):
                    specs.append(
                        i3.Place(
                            bp_name,
                            (bp_cnt_d * bp_spacing,
                             -(height + bp_spacing + len(self.electrical_links) * self.wire_spacing))
                        )
                    )
                else:
                    specs.append(
                        i3.Place(
                            bp_name,
                            (bp_cnt_d * bp_spacing - 3.5 * bp_spacing / 2,
                             -(height + bp_spacing + len(self.electrical_links) * self.wire_spacing + 127))
                        )
                    )
                bp_cnt_d = bp_cnt_d + 1
        return specs

    def _default_external_port_names(self):
        epn = dict()
        epn["gr_in:vertical_io"] = "in"
        epn["gr_out:vertical_io"] = "out"
        bp_cnt = 0
        for el_link in self.electrical_links:
            bp_name = el_link[1].split(":")[0]
            epn[bp_name] = "bp_{}".format(bp_cnt)
            bp_cnt = bp_cnt + 1
        return epn

    class Layout(CircuitCell.Layout):
        def _generate_elements(self, elems):
            insts = self.instances
            up_link = [el for el in self.electrical_links if
                       get_port_from_interface(port_id=el[1], inst_dict=insts).y > 0]
            down_link = [el for el in self.electrical_links if
                         get_port_from_interface(port_id=el[1], inst_dict=insts).y < 0]
            cnt = 0
            cnt_x = 0
            n_links = len(up_link)
            problem_route = []
            # Loop over each electrical link to provide the route for them
            mzi_num = 0
            last_sp = None
            last_ep = None
            ht_num = 0
            dy = -500
            for el_link in up_link:
                sp = get_port_from_interface(port_id=el_link[0], inst_dict=insts)  # Start port
                ep = get_port_from_interface(port_id=el_link[1], inst_dict=insts)  # End port
                bp_name = el_link[1].split(":")[0]
                if re.search("ht", bp_name):
                    mzi_num = -1
                    ht_num = ht_num + 1
                if mzi_num != int(re.findall(r"\d+", bp_name)[1]):
                    if not re.search("ht", bp_name):
                        mzi_num = int(re.findall(r"\d+", bp_name)[1])
                        cnt_x = 0
                    else:
                        if ht_num == 1:
                            cnt_x = 0
                d = self.wire_spacing
                cnt_x = cnt_x + 1

                print(bp_name, cnt)
                shape = None
                if re.search("elec1", bp_name):
                    if sp.x - (n_links / 2 - cnt_x) * d > ep.x:
                        cnt = cnt + 1
                    else:
                        cnt = cnt - 1
                    shape = i3.Shape([
                        sp,
                        (sp.x - (n_links / 2 - cnt_x) * d, sp.y),
                        (sp.x - (n_links / 2 - cnt_x) * d, ep.y - self.bond_pads_spacing + cnt * d + dy),
                        (ep.x, ep.y - self.bond_pads_spacing + cnt * d + dy),
                        ep
                    ])
                    last_sp = sp
                    last_ep = ep
                else:
                    tmp_cnt = None
                    if last_sp.x - (n_links / 2 - (cnt_x - 1)) * d - 2 * d > last_ep.x:
                        cnt = cnt + 1
                        tmp_cnt = cnt - 2
                    else:
                        cnt = cnt - 1
                        tmp_cnt = cnt + 2
                    shape = i3.Shape([
                        sp,
                        (sp.x, sp.y - d),
                        (last_sp.x - (n_links / 2 - cnt_x) * d - 2 * d, sp.y - d),
                        (last_sp.x - (n_links / 2 - cnt_x) * d - 2 * d,
                         last_ep.y - self.bond_pads_spacing + tmp_cnt * d + dy),
                        (ep.x, last_ep.y - self.bond_pads_spacing + tmp_cnt * d + dy),
                        ep
                    ])
                elems += i3.Path(shape=shape, layer=i3.Layer(2), line_width=4.0)

            # down links
            ht_num = 0
            n_links = len(down_link)
            cnt = 0
            cnt_x = 0
            mzi_num = 0
            dy = -dy
            # Loop over each electrical link to provide the route for them
            for el_link in down_link:
                sp = get_port_from_interface(port_id=el_link[0], inst_dict=insts)  # Start port
                ep = get_port_from_interface(port_id=el_link[1], inst_dict=insts)  # End port
                bp_name = el_link[1].split(":")[0]
                if re.search("ht", bp_name):
                    mzi_num = -1
                    ht_num = ht_num + 1
                if mzi_num != int(re.findall(r"\d+", bp_name)[1]):
                    if not re.search("ht", bp_name):
                        mzi_num = int(re.findall(r"\d+", bp_name)[1])
                        #cnt = cnt - 3
                        cnt_x = 0
                    else:
                        if ht_num == 1:
                            cnt_x = 3
                d = self.wire_spacing
                cnt_x = cnt_x + 1
                shape = None
                if re.search("elec1", bp_name):
                    if sp.x - (n_links / 2 - cnt_x) * d > ep.x:
                        cnt = cnt + 1
                    else:
                        cnt = cnt - 1
                    shape = i3.Shape([
                        sp,
                        (sp.x - (n_links / 2 - cnt_x) * d, sp.y),
                        (sp.x - (n_links / 2 - cnt_x) * d, ep.y + self.bond_pads_spacing - cnt * d + dy),
                        (ep.x, ep.y + self.bond_pads_spacing - cnt * d + dy),
                        ep
                    ])
                    last_sp = sp
                    last_ep = ep
                else:
                    tmp_cnt = None
                    if last_sp.x - (n_links / 2 - (cnt_x - 1)) * d - 2 * d > last_ep.x:
                        cnt = cnt + 1
                        tmp_cnt = cnt - 2
                    else:
                        cnt = cnt - 1
                        tmp_cnt = cnt + 2
                    shape = i3.Shape([
                        sp,
                        (sp.x, sp.y + d),
                        (last_sp.x - (n_links / 2 - cnt_x) * d - 2 * d, sp.y + d),
                        (last_sp.x - (n_links / 2 - cnt_x) * d - 2 * d,
                         last_ep.y + self.bond_pads_spacing - tmp_cnt * d + dy),
                        (ep.x, last_ep.y + self.bond_pads_spacing - tmp_cnt * d + dy),
                        ep
                    ])
                # print(bp_name, mzi_num, cnt_x, sp.x - (n_links / 2 - cnt_x) * d)
                elems += i3.Path(shape=shape, layer=i3.Layer(2), line_width=4.0)
                # elems += i3.Path(shape=shape, layer=i3.TECH.PPLAYER.M1, line_width=4.0)
            return elems

    class Netlist(CircuitCell.Netlist):
        def _generate_netlist(self, netlist):
            netlist = super(CircuitCell.Netlist, self)._generate_netlist(self)  # Optical netlist

            for p1, p2 in self.electrical_links:
                term_name = p1.split(":")[1]
                netlist += i3.ElectricalTerm(name=term_name)  # Adding an output term
                del (netlist.instances["bp_{}".format(term_name)])  # Deleting the bondpads from the netlist
                netlist.link("dut:{}".format(term_name), term_name)  # Linking the dut to the bondpads
            return netlist
