from ipcore.exceptions.exc import PropertyValidationError

from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, bezier_sbend
from PhMZI import PhMZI


class Celment(CircuitCell):
    _name_prefix = "Celment"
    block = i3.ChildCellProperty("building block")
    spacing = i3.PositiveNumberProperty(default=2000.0, doc="the spacing between building units")
    rows = i3.IntProperty(default=4, doc="rows of Celment")
    columns = i3.IntProperty(default=3, doc="columns of Celment")

    def validate_properties(self):
        if self.rows % 2 == 1:
            raise PropertyValidationError("Number of rows should be even but given rows is odd: {}".format(self.rows))
        return True

    def _default_block(self):
        return PhMZI()

    def _default_child_cells(self):
        child_cells = dict()
        n_ports = self.rows + 1
        for i in range(n_ports):
            child_cells["gr_in_{}".format(i)] = pdk.GC_TE_1550()
            child_cells["gr_out_{}".format(i)] = pdk.GC_TE_1550()

        rows = self.rows
        columns = self.columns
        for i in range(rows):
            cols = columns - 1 + i % 2
            for j in range(cols):
                child_cells["block_{}_{}".format(i, j)] = self.block
                print("block_{}_{}".format(i, j))

        return child_cells

    def _default_connectors(self):
        conn = []
        rows = self.rows
        cols = self.columns

        # the 1st row
        conn.append(("gr_in_0:wg", "block_0_0:in2", bezier_sbend, {"bend_radius": 5.0}))
        for i in range(cols - 2):
            conn.append(("block_0_{}:out2".format(i), "block_0_{}:in2".format(i + 1), bezier_sbend, {"bend_radius": 5.0}))
            conn.append(("block_0_{}:out1".format(i), "block_{}_{}:in2".format(1, i + 1), bezier_sbend, {"bend_radius": 5.0}))
        conn.append(("block_0_{}:out1".format(cols - 2), "block_{}_{}:in2".format(1, cols - 1), bezier_sbend, {"bend_radius": 5.0}))
        conn.append(("block_0_{}:out2".format(cols - 2), "gr_out_0:wg", bezier_sbend, {"bend_radius": 5.0}))

        for i in range(1, rows - 1):
            for j in range(cols - 1):
                if i % 2 == 1:
                    if j == 0:
                        # left side
                        conn.append(("gr_in_{}:wg".format(i), "block_{}_{}:in2".format(i, j), bezier_sbend,
                                 {"bend_radius": 5.0}))
                        conn.append(("gr_in_{}:wg".format(i + 1), "block_{}_{}:in1".format(i, j), bezier_sbend,
                                 {"bend_radius": 5.0}))
                        #right side
                        conn.append(("block_{}_{}:out1".format(i, cols - 1), "gr_out_{}:wg".format(i + 1), bezier_sbend,
                                    {"bend_radius": 5.0}))
                        conn.append(("block_{}_{}:out2".format(i, cols - 1), "gr_out_{}:wg".format(i), bezier_sbend,
                                     {"bend_radius": 5.0}))
                    conn.append(("block_{}_{}:out1".format(i, j), "block_{}_{}:in2".format(i + 1, j), bezier_sbend,
                                 {"bend_radius": 5.0}))
                    conn.append(("block_{}_{}:out2".format(i, j), "block_{}_{}:in1".format(i - 1, j), bezier_sbend,
                                 {"bend_radius": 5.0}))
                else:
                    conn.append(("block_{}_{}:out1".format(i, j), "block_{}_{}:in2".format(i + 1, j + 1), bezier_sbend,
                                 {"bend_radius": 5.0}))
                    conn.append(("block_{}_{}:out2".format(i, j), "block_{}_{}:in1".format(i - 1, j + 1), bezier_sbend,
                                 {"bend_radius": 5.0}))

        # the last row
        conn.append(("gr_in_{}:wg".format(rows - 1), "block_{}_0:in2".format(rows - 1), bezier_sbend, {"bend_radius": 5.0}))
        conn.append(("gr_in_{}:wg".format(rows), "block_{}_0:in1".format(rows - 1), bezier_sbend, {"bend_radius": 5.0}))
        for i in range(cols - 1):
            conn.append(
                ("block_{}_{}:out1".format(rows - 1, i), "block_{}_{}:in1".format(rows - 1, i + 1), bezier_sbend, {"bend_radius": 5.0}))
            conn.append(
                ("block_{}_{}:out2".format(rows - 1, i), "block_{}_{}:in1".format(rows - 2, i), bezier_sbend,
                 {"bend_radius": 5.0}))
        conn.append(("block_{}_{}:out1".format(rows - 1, cols - 1), "gr_out_{}:wg".format(rows), bezier_sbend, {"bend_radius": 5.0}))
        conn.append(("block_{}_{}:out2".format(rows - 1, cols - 1), "gr_out_{}:wg".format(rows - 1), bezier_sbend, {"bend_radius": 5.0}))

        return conn

    def _default_place_specs(self):
        place_specs = []
        offset = - self.block.get_default_view(i3.LayoutView).size_info().east / 2
        spacing = self.spacing
        spacing_y = 127
        rows = self.rows
        cols = self.columns

        # place the in-ports and out-ports
        for i in range(rows + 1):
            place_specs.append(i3.Place("gr_in_{}".format(i), (-spacing, -spacing_y / 2 + spacing_y * i)))
            place_specs.append(i3.Place("gr_out_{}".format(i), ((cols - 1) * spacing, -spacing_y / 2 + spacing_y * i)))
            place_specs.append(i3.FlipH("gr_out_{}".format(i)))

        for i in range(rows):
            col = cols  - 1 + i % 2
            for j in range(col):
                if i % 2 == 0:
                    place_specs.append(i3.Place("block_{}_{}".format(i, j), (j * spacing + offset, spacing_y / 2 + i * spacing_y)))
                else:
                    place_specs.append(
                        i3.Place("block_{}_{}".format(i, j), (j * spacing - spacing / 2 + offset, spacing_y / 2 + i * spacing_y)))
        return place_specs


    def _default_external_port_names(self):
        epn = dict()

        return epn







