import sys, os
sys.path.append(os.path.join(os.pardir, 'luceda_academy_35-120', 'additional_utils'))
sys.path.append("C:\CSiP180Al\ipkiss")

from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, bezier_sbend


class SplitterTree(CircuitCell):
    _name_prefix = "SPLITTER_TREE"
    splitter = i3.ChildCellProperty(doc="Splitter used")
    levels = i3.IntProperty(default=3, doc="Number of levels")
    spacing_x = i3.PositiveNumberProperty(default=150.0, doc="Horizontal spacing between the levels")
    spacing_y = i3.PositiveNumberProperty(default=50.0, doc="Vertical spacing between the MMIs in the last level")
    bend_radius = i3.PositiveNumberProperty(default=5.0, doc="Bend radius of the connecting waveguides")

    #
    def _default_splitter(self):
        return pdk.M1X2_TE_1550()

    #
    def _default_child_cells(self):
        child_cells = dict()
        n_levels = self.levels
        for lev in range(n_levels):
            n_splitters = int(2 ** lev)  # Number of splitters per level
            for sp in range(n_splitters):
                child_cells["sp_{}_{}".format(lev, sp)] = self.splitter
        return child_cells

    #
    def _default_connectors(self):
        conn = []
        n_levels = self.levels
        for lev in range(1, n_levels):
            n_splitters = int(2 ** lev)  # Number of splitters per level
            for sp in range(n_splitters):
                if sp % 2 == 0:
                    in_port = "sp_{}_{}:out_2".format(lev - 1, int(sp / 2.0))
                else:
                    in_port = "sp_{}_{}:out_1".format(lev - 1, int(sp / 2.0))
                out_port = "sp_{}_{}:in_1".format(lev, sp)
                conn.append((in_port, out_port, bezier_sbend, {"bend_radius": self.bend_radius}))
        return conn

    #
    def _default_place_specs(self):
        place_specs = []
        n_levels = self.levels
        spacing_x = self.spacing_x
        spacing_y = self.spacing_y
        for lev in range(n_levels):
            n_splitters = int(2 ** lev)  # Number of splitters per level
            y_0 = - 0.5 * spacing_y * 2 ** (n_levels - 1)
            for sp in range(n_splitters):
                x_coord = lev * spacing_x
                y_coord = y_0 + (sp + 0.5) * spacing_y * 2 ** (n_levels - lev - 1)
                place_specs.append(
                    i3.Place("sp_{}_{}".format(lev, sp), (x_coord, y_coord))
                )
        return place_specs

    #
    def _default_external_port_names(self):
        epn = {"sp_{}_{}:in_1".format(0, 0): "in"}
        cnt = 1
        lev = self.levels - 1
        n_splitters = int(2 ** lev)  # Number of splitters per level
        for sp in range(n_splitters):
            epn["sp_{}_{}:out_1".format(lev, sp)] = "out_{}".format(cnt)
            cnt += 1
            epn["sp_{}_{}:out_2".format(lev, sp)] = "out_{}".format(cnt)
            cnt += 1
        return epn