from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, manhattan
from circuit.utils import get_port_from_interface
import re
from cel_ocdc_cel import CelOCDCCel
from bond_pad import BondPad


class RoutedCelOCDCCel(CircuitCell):
    _name_prefix = "routed celment-ocdc-celment"
    dut = i3.ChildCellProperty(doc="celment-ocdc-celment")
    electrical_links=i3.LockedProperty(doc="The electrical connectors between the heaters and the contact pads")
    bond_pads_spacing_x = i3.PositiveNumberProperty(default=110.0,
                                                    doc="The horizontal distance between the contact pads")
    bond_pads_spacing_y = i3.PositiveNumberProperty(default=100.0,
                                                    doc="The vertical distance between the contact pads")
    wire_spacing = i3.PositiveNumberProperty(default=10.0, doc="The spacing between the electrical wires")

    def _default_dut(self):
        return CelOCDCCel()

    def _default_electrical_links(self):
        conn = []
        return conn

    def _default_child_cells(self):
        child_cells = dict()
        child_cells["dut"] = self.dut
        npads = 96
        for i in range(npads):
            child_cells["bp_ht{}_elec1".format(i)] = BondPad()
            child_cells["bp_ht{}_elec2".format(i)] = BondPad()

        return child_cells

    def _default_place_specs(self):
        west = self.dut.get_default_view(i3.LayoutView).size_info().west
        dut_length = self.dut.get_default_view(i3.LayoutView).size_info().east - west
        print("length: ", dut_length)
        south = self.dut.get_default_view(i3.LayoutView).size_info().south
        dut_height = (self.dut.get_default_view(i3.LayoutView).size_info().north - south)
        print("height: ", dut_height)
        place_specs = [i3.Place("dut", (-west, -dut_height / 2 - south))]
        bp_xlen = 60
        bp_ylen = 80
        displacement = self.dut.get_default_view(i3.LayoutView).size_info().west + 300
        cnt = 0
        # up pads
        while cnt < 36:
            place_specs.append(i3.Place("bp_ht{}_elec1".format(cnt),
                                        (100 + bp_xlen / 2 + cnt * self.bond_pads_spacing_x,
                                         2500 - (100 + bp_ylen / 2))))
            place_specs.append(i3.Place("bp_ht{}_elec2".format(cnt),
                                        (100 + bp_xlen / 2 + (cnt + 0.5) * self.bond_pads_spacing_x,
                                         2500 - (100 + bp_ylen / 2 + self.bond_pads_spacing_y))))
            cnt = cnt + 1
        # down pads
        while cnt < 72:
            place_specs.append(i3.Place("bp_ht{}_elec1".format(cnt),
                                        (100 + bp_xlen / 2 + (cnt - 35) * self.bond_pads_spacing_x,
                                         -2500 + (100 + bp_ylen / 2))))
            place_specs.append(i3.Place("bp_ht{}_elec2".format(cnt),
                                        (100 + bp_xlen / 2 + (cnt - 35 + 0.5) * self.bond_pads_spacing_x,
                                         - 2500 + (100 + bp_ylen / 2 + self.bond_pads_spacing_y))))
            cnt = cnt + 1

        bp_x = 4800
        displacement = 1200
        # right pads
        while cnt < 96:
            place_specs.append(i3.Place("bp_ht{}_elec1".format(cnt),
                                        (bp_x, displacement - (cnt - 75) * self.bond_pads_spacing_x),
                                        angle=90))
            place_specs.append(i3.Place("bp_ht{}_elec2".format(cnt),
                                        (bp_x + 100 + bp_ylen / 2,
                                         displacement - (cnt - 75) * self.bond_pads_spacing_x - 0.5 * self.bond_pads_spacing_x),
                                        angle=90))
            cnt = cnt + 1
        return place_specs



