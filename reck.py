from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, bezier_sbend
from PhMZI import PhMZI


class Reck(CircuitCell):
    _name_prefix = "Reck"
    block = i3.ChildCellProperty("building block")
    spacing = i3.PositiveNumberProperty(default=50.0, doc="the spacing between building block")
    levels = i3.IntProperty(default=3, doc="levels of Reck")

    def _default_block(self):
        return PhMZI()

    def _default_child_cells(self):
        child_cells = dict()
        levels = self.levels
        for i in range(levels):
            for j in range(i + 1):
                child_cells["block_{}_{}".format(i, j)] = self.block

        for i in range(levels + 1):
            child_cells["gr_in_{}".format(i)] = pdk.GC_TE_1550()
            child_cells["gr_out_{}".format(i)] = pdk.GC_TE_1550()

        return child_cells

    def _default_connectors(self):
        conn = []
        levels = self.levels
        # the body net connection
        for i in range(levels - 1):
            for j in range(i + 1):
                conn.append(("block_{}_{}:in1".format(i, j), "block_{}_{}:out2".format(i + 1, j), bezier_sbend, {"bend_radius": 5.0}))
                conn.append(("block_{}_{}:out1".format(i, j), "block_{}_{}:in2".format(i + 1, j + 1), bezier_sbend, {"bend_radius": 5.0}))


        # the tail connection
        for i in range(levels - 1):
                conn.append(("block_{}_{}:out1".format(levels - 1, i), "block_{}_{}:in1".format(levels - 1, i + 1),
                             bezier_sbend, {"bend_radius": 5.0}))

        # the input and output
        for i in range(levels):
            conn.append(("gr_in_{}:wg".format(i), "block_{}_0:in2".format(i), bezier_sbend, {"bend_radius": 5.0}))
            conn.append(("block_{}_{}:out2".format(i, i), "gr_out_{}:wg".format(i), bezier_sbend, {"bend_radius": 5.0}))

        conn.append(("gr_in_{}:wg".format(levels), "block_{}_0:in1".format(levels - 1), bezier_sbend, {"bend_radius": 5.0}))
        conn.append(
            ("block_{}_{}:out1".format(levels - 1, levels - 1), "gr_out_{}:wg".format(levels), bezier_sbend, {"bend_radius": 5.0}))
        return conn

    def _default_place_specs(self):
        place_specs = []
        levels = self.levels
        offset = - self.block.get_default_view(i3.LayoutView).size_info().east / 2
        spacing = 20 * self.spacing
        spacing_y = 127

        for i in range(levels + 1):
            place_specs.append(i3.Place("gr_in_{}".format(i), (-float(levels)/2 * spacing*2 + offset, i * spacing_y)))
            place_specs.append(i3.Place("gr_out_{}".format(i), (float(levels)/2 * spacing*2 - offset, i * spacing_y)))
            place_specs.append(i3.FlipH("gr_out_{}".format(i)))

        for i in range(levels):
            for j in range(i + 1):
                place_specs.append(i3.Place("block_{}_{}".format(i, j), (-float(i)/2 * spacing*2 + j * spacing*2 + offset, (i + 0.5) * spacing_y)))
                print(i,j, (-float(i)/2 * spacing*2 + j * 2* spacing, (i + 0.5) * spacing_y))
        return place_specs

    def _default_external_port_names(self):
        epn = dict()

        return epn
