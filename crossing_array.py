from si_fab import technology
from si_fab.all import Crossing
from circuit.all import CircuitCell, bezier_sbend
from ipkiss3 import all as i3

class CrossingArray(CircuitCell):
    _name_prefix = "Crossing Array"
    level = i3.PositiveIntProperty(default=5, doc="level of crossing array")
    crossing_block = i3.ChildCellProperty(doc="unit block of the crossing array")
    spacing = i3.PositiveNumberProperty(default=10, doc="spacing between the crossing blocks")
    bend_radius = i3.PositiveNumberProperty(default=5.0, doc="Bend radius of the connecting waveguides")

    def _default_crossing_block(self):
        return Crossing()

    def _default_child_cells(self):
        child_cells = dict()
        for i in range(self.level, 0, -1):
            for j in range(i):
                child_cells["crossing_{}_{}".format(i, j)] = self.crossing_block
        return child_cells

    def _default_place_specs(self):
        place_specs = []
        for i in range(self.level, 0, -1):
            for j in range(i):
                place_specs.append(i3.Place("crossing_{}_{}".format(i, j), (j * self.spacing, (self.level - i) * self.spacing)))
        return place_specs

    def _default_connectors(self):
        conn = []
        for i in range(self.level, 1, -1):
            for j in range(i - 1):
                conn.append(("crossing_{}_{}:out1".format(i,j), "crossing_{}_{}:in1".format(i, j + 1)))
                conn.append(("crossing_{}_{}:out2".format(i, j), "crossing_{}_{}:in2".format(i - 1, j)))
        return conn


