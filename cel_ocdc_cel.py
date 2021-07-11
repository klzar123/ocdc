from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, bezier_sbend, manhattan
from bond_pad import BondPad
import re
from time import time
from functools import wraps, partial

from ocdc import OCDC
from celment import Celment


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
    level = i3.PositiveIntProperty(default=4, doc="level of OCDC")
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
        gr_out_x = 2 * celment_height + 2 * self.spacing_x + ocdc_len
        for i in range(self.dim):
            place_specs.append(i3.Place("gr_in_{}".format(i), (celment_height - i * cel_spy, -2000), angle=90))
            place_specs.append(i3.Place("gr_out_{}".format(i), (gr_out_x - i * cel_spy, 2000), angle=90))
            place_specs.append(i3.FlipH("gr_out_{}".format(i)))

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
        for i in range(self.dim):
            conn.append(("gr_in_{}:wg".format(i), "cel_in:in{}".format(i + 1),
                         manhattan, {"bend_radius": self.bend_radius}))
            c = partial(manhattan, control_points=[(celment_height - cel_spy/2 - i * cel_spy, celment_len / 2 + i * wg_spacing),
                                                   (ocdc_x - (self.dim - i) * wg_spacing, celment_len / 2 + i * wg_spacing),
                                                   (ocdc_x - (self.dim - i) * wg_spacing, ocdc_displacement + i * ocdc_spacing)])
            conn.append(("cel_in:out{}".format(i + 1), "ocdc_{}:in".format(i),
                         c, {"bend_radius": self.bend_radius}))
            c = partial(manhattan, control_points=[(ocdc_x + ocdc_len + (i + 1) * wg_spacing, ocdc_displacement + i * ocdc_spacing),
                                                   (ocdc_x + ocdc_len + (i + 1) * wg_spacing, -celment_len / 2 - (self.dim - i) * wg_spacing),
                                                   (gr_out_x - i * cel_spy, -celment_len / 2 - (self.dim - i) * wg_spacing)])
            conn.append(("ocdc_{}:out".format(i), "cel_out:in{}".format(self.dim - i),
                         c, {"bend_radius": self.bend_radius}))
            conn.append(("cel_out:out{}".format(self.dim - i), "gr_out_{}:wg".format(i),
                         manhattan, {"bend_radius": self.bend_radius}))
        return conn
