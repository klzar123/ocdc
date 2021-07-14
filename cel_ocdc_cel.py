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
        return OCDC(levels=self.level, mzi_nums=2, plus_in=True)

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
        child_cells["gr_ocdc0_out"] = pdk.GC_TE_1550()
        child_cells["gr_ocdc2_out"] = pdk.GC_TE_1550()
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
            place_specs.append(i3.Place("gr_in_{}".format(i), (gr_x, gr_displacement - (4 + i) * cel_spy)))
        place_specs.append(i3.Place("gr_ocdc2_out", (gr_x, gr_displacement - self.dim * cel_spy)))
        place_specs.append(i3.Place("gr_ocdc0_out", (gr_x, gr_displacement - (2 * self.dim + 1) * cel_spy)))
        place_specs.append(i3.Place("ref_gr_in", (gr_x, gr_displacement - (2 * self.dim + 2) * cel_spy)))
        place_specs.append(i3.Place("ref_gr_out", (gr_x, gr_displacement - (2 * self.dim + 3) * cel_spy)))

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
        delta_displacement = 11
        # 2. the celments and gratings
        for i in range(self.dim):
            c = partial(manhattan, control_points=[(gr_out_x - i * cel_spy, celment_len / 2 + (self.dim - i + delta_displacement) * wg_spacing),
                                                   (gr_x + (i + 2) * wg_spacing, celment_len / 2 + (self.dim - i + delta_displacement) * wg_spacing),
                                                   (gr_x + (i + 2) * wg_spacing, gr_displacement - i * cel_spy)])
            conn.append(("cel_out:out{}".format(self.dim - i), "gr_out_{}:wg".format(self.dim - i - 1),
                        c, {"bend_radius":self.bend_radius}))
            c = partial(manhattan, control_points=[(celment_height - cel_spy/2 - i * cel_spy, celment_len / 2 + (self.dim - i + delta_displacement - 4) * wg_spacing),
                                                   (gr_x + (i + 6) * wg_spacing, celment_len / 2 + (self.dim - i + delta_displacement - 4) * wg_spacing),
                                                   (gr_x + (i + 6) * wg_spacing, gr_displacement - (i + 4) * cel_spy)])
            conn.append(("cel_in:out{}".format(i + 1), "gr_in_{}:wg".format(i),
                         c, {"bend_radius": self.bend_radius}))
        # ocdc0_out
        c = partial(manhattan, control_points=[(ocdc_x + ocdc_len + 0.5 * wg_spacing, ocdc_displacement - 1.5),
                                               (ocdc_x + ocdc_len + 0.5 * wg_spacing, ocdc_displacement - ocdc_height / 2 + 90),
                                               (gr_x + 3 * wg_spacing, ocdc_displacement - ocdc_height / 2 + 90)])
        conn.append(("ocdc_0:out2", "gr_ocdc0_out:wg", c, {"bend_radius": self.bend_radius}))
        # ocdc2_out
        i = 3
        c = partial(manhattan, control_points=[(ocdc_x + ocdc_len + 0.5 * wg_spacing,
                                                ocdc_displacement + 2 * ocdc_spacing +  1.5),
                                               (ocdc_x + ocdc_len + 0.5 * wg_spacing,
                                                celment_len / 2 + (self.dim - i + delta_displacement) * wg_spacing),
                                               (gr_x + (i + 2) * wg_spacing,
                                                celment_len / 2 + (self.dim - i + delta_displacement) * wg_spacing),
                                               (gr_x + (i + 2) * wg_spacing, gr_displacement - i * cel_spy)])
        conn.append(("ocdc_2:out1", "gr_ocdc2_out:wg", c, {"bend_radius": self.bend_radius}))

        # 3. the celment and ocdcs:
        delta_y = 0
        for i in range(self.dim):
            if i == 0:
                delta_y = 800
            else:
                delta_y = 200
            c = partial(manhattan, control_points=[(celment_height - cel_spy/2 - i * cel_spy, -(celment_len / 2 + i * wg_spacing) + delta_y),
                                                   (ocdc_x - (self.dim - i) * wg_spacing, -(celment_len / 2 + i * wg_spacing) + delta_y),
                                                   (ocdc_x - (self.dim - i) * wg_spacing, ocdc_displacement + (self.dim - i - 1) * ocdc_spacing)])
            conn.append(("cel_in:in{}".format(i + 1), "ocdc_{}:in".format(self.dim - i - 1),
                         c, {"bend_radius": self.bend_radius}))
            if i == 2:
                delta_y = 500
            else:
                delta_y = 200
            if i != 0:
                op_id = 2
                c = partial(manhattan, control_points=[
                    (ocdc_x + ocdc_len + (i + 1) * wg_spacing, ocdc_displacement + i * ocdc_spacing),
                    (ocdc_x + ocdc_len + (i + 1) * wg_spacing, -celment_len / 2 - (self.dim - i) * wg_spacing + delta_y),
                    (gr_out_x - i * cel_spy, -celment_len / 2 - (self.dim - i) * wg_spacing + delta_y)])
                conn.append(("ocdc_{}:out{}".format(i, op_id), "cel_out:in{}".format(self.dim - i),
                             c, {"bend_radius": self.bend_radius}))
            else:
                op_id = 1
                #c = partial(manhattan, control_points=[
                #    (ocdc_x + ocdc_len + (i + 1) * wg_spacing, ocdc_displacement + i * ocdc_spacing + 1.5),
                #    (ocdc_x + ocdc_len + (i + 1) * wg_spacing, -celment_len / 2 - (self.dim - i) * wg_spacing + delta_y + 1.5),
                #    (gr_out_x - i * cel_spy - 98, -celment_len / 2 - (self.dim - i) * wg_spacing + delta_y)])
                conn.append(("ocdc_{}:out{}".format(i, op_id), "cel_out:in{}".format(self.dim - i),
                             manhattan, {"bend_radius": self.bend_radius}))
        return conn
    def _default_external_port_names(self):
        epn = dict()
        # the input and output
        for i in range(self.dim):
            epn["gr_in_{}:vertical_io".format(i)] = "in{}".format(i +1)
            epn["gr_out_{}:vertical_io".format(i)] = "out{}".format(i + 1)
        epn["ref_gr_in"] = "ref_in"
        epn["ref_gr_out"] = "ref_out"
        epn["gr_ocdc0_out"] = "ocdc_out_0"
        epn["gr_ocdc2_out"] = "ocdc_out_1"
        return epn

    def _default_propagated_electrical_ports(self):
        pep = []
        # cel_in and cel_out
        for i in range(self.dim):
            n_units = (self.dim - self.dim % 2) / 2 + self.dim % 2 * (i % 2)
            # cel_in and cel_out
            for j in range(n_units):
                pep.append("cel_in_block_{}_{}_mzi_arm1_elec1".format(i, j))
                pep.append("cel_in_block_{}_{}_mzi_arm1_elec2".format(i, j))
                pep.append("cel_in_block_{}_{}_mzi_arm2_elec1".format(i, j))
                pep.append("cel_in_block_{}_{}_mzi_arm2_elec2".format(i, j))
                pep.append("cel_in_block_{}_{}_ht_elec1".format(i, j))
                pep.append("cel_in_block_{}_{}_ht_elec2".format(i, j))
                pep.append("cel_out_block_{}_{}_mzi_arm1_elec1".format(i, j))
                pep.append("cel_out_block_{}_{}_mzi_arm1_elec2".format(i, j))
                pep.append("cel_out_block_{}_{}_mzi_arm2_elec1".format(i, j))
                pep.append("cel_out_block_{}_{}_mzi_arm2_elec2".format(i, j))
                pep.append("cel_out_block_{}_{}_ht_elec1".format(i, j))
                pep.append("cel_out_block_{}_{}_ht_elec2".format(i, j))
            # ocdc
            mzi_string_nums = 2 ** self.level - 1
            for j in range(mzi_string_nums):
                if j < 2:
                    continue
                for k in range(2):
                    pep.append("ocdc_{}_mzi_{}_{}_arm1_elec1".format(i, j, k))
                    pep.append("ocdc_{}_mzi_{}_{}_arm1_elec2".format(i, j, k))
                    pep.append("ocdc_{}_mzi_{}_{}_arm2_elec1".format(i, j, k))
                    pep.append("ocdc_{}_mzi_{}_{}_arm2_elec2".format(i, j, k))
                pep.append("ocdc_{}_ht_wg_{}_elec1".format(i, j))
                pep.append("ocdc_{}_ht_wg_{}_elec2".format(i, j))
            pep.append("ocdc_{}_ht_wg_{}_elec1".format(i, mzi_string_nums))
            pep.append("ocdc_{}_ht_wg_{}_elec2".format(i, mzi_string_nums))
        return pep





