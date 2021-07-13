from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, bezier_sbend, manhattan
from bond_pad import BondPad
import re
from time import time
from functools import wraps, partial

from ocdc import OCDC
from celment import Celment
from bond_pad import BondPad


def timethis(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time()
        r = func(*args, **kwargs)
        end = time()
        print(end - start)
        return r
    return wrapper


class CelOCDCCel(CircuitCell):
    _name_prefix = "Celment-OCDC-Celment"
    celment_block = i3.ChildCellProperty(doc="Celment")
    ocdc_block = i3.ChildCellProperty(doc="OCDC")
    dim = i3.PositiveIntProperty(default=3, doc="dimension of celment")
    level = i3.PositiveIntProperty(default=3, doc="level of OCDC")
    spacing_x = i3.PositiveNumberProperty(default=200, doc="spacing between celment and OCDC")
    spacing_y = i3.PositiveNumberProperty(default=100, doc="spacing between OCDCs")
    bend_radius = i3.PositiveNumberProperty(default=10.0, doc="Bend radius of the connecting waveguides")

    def _default_celment_block(self):
        return Celment(dim=self.dim)

    def _default_ocdc_block(self):
        return OCDC(levels=self.level, mzi_nums=2)

    @timethis
    def _default_child_cells(self):
        child_cells = dict()
        child_cells["cel_in"] = self.celment_block
        child_cells["cel_out"] = self.celment_block
        for i in range(self.dim):
            child_cells["ocdc_{}".format(i)] = self.ocdc_block
            child_cells["gr_in_{}".format(i)] = pdk.GC_TE_1550()
            child_cells["gr_out_{}".format(i)] = pdk.GC_TE_1550()
        child_cells["ref_gr_in"] = pdk.GC_TE_1550()
        child_cells["ref_gr_out"] = pdk.GC_TE_1550()
        return child_cells

    @timethis
    def _default_place_specs(self):
        place_specs = []

        # size info of the child cells
        # gr_len = self.child_cells["gr_in_0"].get_default_view(i3.LayoutView).size_info().east
        cel_spy = self.celment_block.get_spacing_y()
        cel_spx = self.celment_block.get_spacing_x()
        celment_len = self.celment_block.get_default_view(i3.LayoutView).size_info().east
        celment_height = self.celment_block.get_default_view(i3.LayoutView).size_info().north
        ocdc_len = self.ocdc_block.get_default_view(i3.LayoutView).size_info().east
        ocdc_height = self.ocdc_block.get_default_view(i3.LayoutView).size_info().north - \
                      self.ocdc_block.get_default_view(i3.LayoutView).size_info().south

        # the input and output grating
        gr_displacement = (self.dim + 0.5) * cel_spy
        gr_x = -500
        for i in range(self.dim):
            place_specs.append(i3.Place("gr_out_{}".format(self.dim - i - 1), (gr_x, gr_displacement - i * cel_spy)))
            place_specs.append(i3.Place("gr_in_{}".format(i), (gr_x, gr_displacement - (3 + i) * cel_spy)))
        place_specs.append(i3.Place("ref_gr_in", (gr_x, gr_displacement - 2 * self.dim * cel_spy)))
        place_specs.append(i3.Place("ref_gr_out", (gr_x, gr_displacement - (2 * self.dim + 1) * cel_spy)))

        # the input celment
        place_specs.append(i3.Place("cel_in", (celment_height, - celment_len / 2), angle=90))

        # the ocdcs
        ocdc_spacing = self.spacing_y + ocdc_height
        ocdc_displacement = -((self.dim - 1) / 2.0 * ocdc_spacing)
        ocdc_x = celment_height + self.spacing_x
        for i in range(self.dim):
            place_specs.append(i3.Place("ocdc_{}".format(i), (ocdc_x, ocdc_displacement + i * ocdc_spacing)))

        # the output celment
        place_specs.append(
            i3.Place("cel_out", (celment_height + 2 * self.spacing_x + ocdc_len, -celment_len / 2), angle=90))
        place_specs.append(i3.FlipV("cel_out"))

        return place_specs

    @timethis
    def _default_connectors(self):
        conn = []
        cel_spy = self.celment_block.get_spacing_y()
        cel_spx = self.celment_block.get_spacing_x()
        celment_len = self.celment_block.get_default_view(i3.LayoutView).size_info().east
        celment_height = self.celment_block.get_default_view(i3.LayoutView).size_info().north
        ocdc_len = self.ocdc_block.get_default_view(i3.LayoutView).size_info().east
        ocdc_height = self.ocdc_block.get_default_view(i3.LayoutView).size_info().north - \
                      self.ocdc_block.get_default_view(i3.LayoutView).size_info().south
        ocdc_spacing = self.spacing_y + ocdc_height
        ocdc_displacement = -((self.dim - 1) / 2.0 * ocdc_spacing)
        ocdc_x = celment_height + self.spacing_x
        gr_out_x = 2 * celment_height + 2 * self.spacing_x + ocdc_len
        wg_spacing = 50
        gr_x = -500
        gr_displacement = (self.dim + 0.5) * cel_spy

        # connect the grating and celment
        # 1. the reference grating
        conn.append(("ref_gr_in:wg", "ref_gr_out:wg", manhattan, {"bend_radius":self.bend_radius}))
        delta_displacement = 7
        # 2. the celments and gratings
        for i in range(self.dim):
            c = partial(manhattan, control_points=[(gr_out_x - i * cel_spy, celment_len / 2 + (self.dim - i + delta_displacement) * wg_spacing),
                                                   (gr_x + (i + 2) * wg_spacing, celment_len / 2 + (self.dim - i + delta_displacement) * wg_spacing),
                                                   (gr_x + (i + 2) * wg_spacing, gr_displacement - i * cel_spy)])
            conn.append(("cel_out:out{}".format(self.dim - i), "gr_out_{}:wg".format(self.dim - i - 1),
                        c, {"bend_radius":self.bend_radius}))
            c = partial(manhattan, control_points=[(celment_height - cel_spy/2 - i * cel_spy, celment_len / 2 + (self.dim - i + delta_displacement - 3) * wg_spacing),
                                                   (gr_x + (i + 5) * wg_spacing, celment_len / 2 + (self.dim - i + delta_displacement - 3) * wg_spacing),
                                                   (gr_x + (i + 5) * wg_spacing, gr_displacement - (i + 3) * cel_spy)])
            conn.append(("cel_in:out{}".format(i + 1), "gr_in_{}:wg".format(i),
                         c, {"bend_radius": self.bend_radius}))
        # 3. the celment and ocdcs:
        delta_y = 0
        for i in range(self.dim):
            if i == 0:
                delta_y = 900
            else:
                delta_y = 200
            c = partial(manhattan, control_points=[(celment_height - cel_spy/2 - i * cel_spy, -(celment_len / 2 + i * wg_spacing) + delta_y),
                                                   (ocdc_x - (self.dim - i) * wg_spacing, -(celment_len / 2 + i * wg_spacing) + delta_y),
                                                   (ocdc_x - (self.dim - i) * wg_spacing, ocdc_displacement + (self.dim - i - 1) * ocdc_spacing)])
            conn.append(("cel_in:in{}".format(i + 1), "ocdc_{}:in".format(self.dim - i - 1),
                         c, {"bend_radius": self.bend_radius}))
            if i == 2:
                delta_y = 900
            else:
                delta_y = 200
            c = partial(manhattan, control_points=[(ocdc_x + ocdc_len + (i + 1) * wg_spacing, ocdc_displacement + i * ocdc_spacing),
                                                   (ocdc_x + ocdc_len + (i + 1) * wg_spacing, -celment_len / 2 - (self.dim - i) * wg_spacing  + delta_y),
                                                   (gr_out_x - i * cel_spy, -celment_len / 2 - (self.dim - i) * wg_spacing + delta_y)])
            conn.append(("ocdc_{}:out".format(i), "cel_out:in{}".format(self.dim - i),
                         c, {"bend_radius": self.bend_radius}))
        return conn

    def _default_external_port_names(self):
        epn = dict()
        # the input and output
        for i in range(self.dim):
            epn["gr_in_{}:vertical_io".format(i)] = "in{}".format(i +1)
            epn["gr_out_{}:vertical_io".format(i)] = "out{}".format(i + 1)
        epn["ref_gr_in"] = "ref_in"
        epn["ref_gr_out"] = "ref_out"
        return epn


"""
    def _default_propagated_electrical_ports(self):

    @timethis
    def _default_electrical_links(self):
        elink = []
        # the connection between input/output celment and bond pads
        cel_ports = dict()
        for port in self.celment_block.Layout().ports:
            if not re.search("in|out", port.name):
                cel_ports[port.name] = port.position.x
        o_ports = [k for k, v in sorted(cel_ports.items(), key=lambda item: item[1])]
        idx = 0
        for name in o_ports:
            elink.append(("cel_in:{}".format(name), "bp_cel_in_{}:m1".format(idx)))
            idx = idx + 1
        idx = 0
        for name in o_ports:
            elink.append(("cel_out:{}".format(name), "bp_cel_out_{}:m1".format(idx)))
            idx = idx + 1

        # the connection between ocdcs and bond pads
        return elink
=====>
        # bond pads : for input celment and output celment
        n_pads = 6 * self.dim * (self.dim - 1) / 2
        for i in range(n_pads):
            child_cells["bp_cel_in_{}".format(i)] = BondPad()
            child_cells["bp_cel_out_{}".format(i)] = BondPad()

        # bond pads: for ocdcs
        n_rows = self.child_cells["ocdc_0"].get_n_rows()
        mzi_nums = self.child_cells["ocdc_0"].get_mzi_nums()
        for i in range(self.dim):
            for j in n_rows:
                for k in mzi_nums:
                    if j != n_rows - 1:
                        child_cells["bp_ocdc{}_mzis{}_mzi{}_arm1_elec1".format(i, j, k)] = BondPad()
                        child_cells["bp_ocdc{}_mzis{}_mzi{}_arm1_elec2".format(i, j, k)] = BondPad()
                        child_cells["bp_ocdc{}_mzis{}_mzi{}_arm2_elec1".format(i, j, k)] = BondPad()
                        child_cells["bp_ocdc{}_mzis{}_mzi{}_arm2_elec2".format(i, j, k)] = BondPad()
                child_cells["bp_ocdc{}_ht{}_elec1".format(i, j)] = BondPad()
                child_cells["bp_ocdc{}_ht{}_elec2".format(i, j)] = BondPad()
"""