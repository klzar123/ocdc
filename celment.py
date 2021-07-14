from CSiP180Al import all as pdk
from ipcore.exceptions.exc import PropertyValidationError
from ipkiss3 import all as i3
from circuit.all import CircuitCell, manhattan
from PhMZI import PhMZI
from circuit.utils import get_port_from_interface


class Celment(CircuitCell):
    _name_prefix = ("Celment")
    dim = i3.PositiveIntProperty(default=4, doc="dimension of the celment.")
    unit_block = i3.ChildCellProperty(doc="unit block of celment.")
    spacing_x = i3.PositiveNumberProperty(doc="spacing between the unit blocks in x direction")
    spacing_y = i3.PositiveNumberProperty(doc="spacing between the unit blocks in y direction")
    bend_radius = i3.PositiveNumberProperty(default=10.0, doc="Bend radius of the connecting waveguides")
    f_grating_io = i3.BoolProperty(default=False, doc="if add the grating input and output, value = True")

    _input_list = []
    _output_list = []

    def validate_properties(self):
        if self.dim <= 1:
            raise PropertyValidationError("Dimension of celment should ne greater than 1.")
        return True

    def _default_unit_block(self):
        return PhMZI()

    def _default_spacing_x(self):
        return 2 * self.unit_block.get_default_view(i3.LayoutView).size_info().east + 40

    def _default_spacing_y(self):
        return 1.5 * (self.unit_block.get_default_view(i3.LayoutView).size_info().north -
                      self.unit_block.get_default_view(i3.LayoutView).size_info().south) - 50



    def get_spacing_y(self):
        return self.spacing_y

    def get_spacing_x(self):
        return self.spacing_x

    def _default_child_cells(self):
        child_cells = dict()
        # the unit blocks
        for i in range(self.dim - 1):
            n_units = 0
            if self.dim % 2 == 0:
                n_units = self.dim / 2
            else:
                n_units = (self.dim + 1) / 2 if (i + 1) % 2 == 0 else (self.dim - 1) / 2
            for j in range(n_units):
                child_cells["block_{}_{}".format(i, j)] = self.unit_block
        # the input and out grating
        if self.f_grating_io:
            for i in range(self.dim):
                child_cells["gr_in_{}".format(i)] = pdk.GC_TE_1550()
                child_cells["gr_out_{}".format(i)] = pdk.GC_TE_1550()
        return child_cells

    def _default_place_specs(self):
        offset = self.unit_block.get_default_view(i3.LayoutView).size_info().east / 2
        spacing_x = self.spacing_x
        spacing_y = self.spacing_y
        gr_len = 0
        if self.f_grating_io:
            gr_len = self.child_cells["gr_in_0"].get_default_view(i3.LayoutView).size_info().east

        place_specs = []
        # place the input and output gratings
        if self.f_grating_io:
            for i in range(self.dim):
                place_specs.append(i3.Place("gr_in_{}".format(i), (0, spacing_y * i)))
                place_specs.append(
                    i3.Place("gr_out_{}".format(i), (self.dim / 2 * spacing_x + gr_len + 1200, spacing_y * i)))
                place_specs.append(i3.FlipH("gr_out_{}".format(i)))

        # place the unit blocks
        for i in range(self.dim - 1):
            n_units = 0
            extra_length = 0
            if self.dim % 2 == 0:
                n_units = self.dim / 2
                extra_length = 0 if i % 2 == 0 else spacing_x / 2
            else:
                n_units = (self.dim + 1) / 2 if (i + 1) % 2 == 0 else (self.dim - 1) / 2
                extra_length = spacing_x / 2 if i % 2 == 0 else 0
            for j in range(n_units):
                place_specs.append(i3.Place("block_{}_{}".format(i, j),
                                            (j * spacing_x + 600 + extra_length - offset,
                                             spacing_y * (i + 0.5))))
        return place_specs

    def _default_connectors(self):
        conn = []
        # connect the input grating
        offset = 0
        if self.f_grating_io:
            if self.dim % 2 != 0:
                conn.append(("gr_in_0:wg", "block_0_0:in2", manhattan, {"bend_radius": self.bend_radius}))
                offset = 1
            for i in range(offset, self.dim, 2):
                conn.append(
                    ("gr_in_{}:wg".format(i), "block_{}_0:in2".format(i), manhattan, {"bend_radius": self.bend_radius}))
                conn.append(("gr_in_{}:wg".format(i + 1), "block_{}_0:in1".format(i), manhattan,
                             {"bend_radius": self.bend_radius}))
        else:
            if self.dim % 2 != 0:
                self._input_list.append("block_0_0:in2")
                offset = 1
            for i in range(offset, self.dim, 2):
                self._input_list.append("block_{}_0:in2".format(i))
                self._input_list.append("block_{}_0:in1".format(i))

        for i in range(self.dim - 1):
            n_units = 0
            if self.dim % 2 == 0:
                n_units = self.dim / 2
                offset = i % 2
            else:
                n_units = (self.dim + 1) / 2 if (i + 1) % 2 == 0 else (self.dim - 1) / 2
                offset = (i + 1) % 2
            for j in range(n_units - 1):
                if i + 1 > self.dim - 2:
                    # conn.append(("block_{}_{}:out1".format(i, j), "block_{}_{}:in1".format(i, j + 1), manhattan,
                    #             {"bend_radius": self.bend_radius}))
                    conn.append(("block_{}_{}:out1".format(i, j), "block_{}_{}:in1".format(i, j + 1)))
                else:
                    conn.append((
                        "block_{}_{}:out1".format(i, j), "block_{}_{}:in2".format(i + 1, j + offset), manhattan,
                        {"bend_radius": self.bend_radius}))
                if i - 1 < 0:
                    # conn.append(("block_{}_{}:out2".format(i, j), "block_{}_{}:in2".format(i, j + 1), manhattan,
                    #             {"bend_radius": self.bend_radius}))
                    conn.append(("block_{}_{}:out2".format(i, j), "block_{}_{}:in2".format(i, j + 1)))
                else:
                    conn.append(
                        ("block_{}_{}:out2".format(i, j), "block_{}_{}:in1".format(i - 1, j + offset), manhattan,
                         {"bend_radius": self.bend_radius}))
            # connect the output
            if self.f_grating_io:
                conn.append(("block_0_{}:out2".format((self.dim - self.dim % 2) / 2 - 1), "gr_out_0:wg", manhattan,
                             {"bend_radius": self.bend_radius}))
            else:
                self._output_list.append("block_0_{}:out2".format((self.dim - self.dim % 2) / 2 - 1))
            conn.append(("block_0_{}:out1".format((self.dim - self.dim % 2) / 2 - 1),
                         "block_1_{}:in2".format((self.dim + self.dim % 2) / 2 - 1),
                         manhattan, {"bend_radius": self.bend_radius}))
            for i in range(1, self.dim - 1):
                j = (self.dim - self.dim % 2) / 2 + self.dim % 2 * (i % 2) - 1
                if i % 2 == 1:
                    if self.f_grating_io:
                        conn.append(("block_{}_{}:out2".format(i, j), "gr_out_{}:wg".format(i), manhattan,
                                     {"bend_radius": self.bend_radius}))
                        conn.append(("block_{}_{}:out1".format(i, j), "gr_out_{}:wg".format(i + 1), manhattan,
                                     {"bend_radius": self.bend_radius}))
                    else:
                        self._output_list.append("block_{}_{}:out2".format(i, j))
                        self._output_list.append("block_{}_{}:out1".format(i, j))
                    if i + 1 == self.dim - 2:
                        if self.f_grating_io:
                            conn.append(("block_{}_{}:out1".format(i + 1,
                                                                   (self.dim - self.dim % 2) / 2 + self.dim % 2 * (
                                                                               (i + 1) % 2) - 1),
                                         "gr_out_{}:wg".format(i + 2), manhattan,
                                         {"bend_radius": self.bend_radius}))
                        else:
                            self._output_list.append("block_{}_{}:out1".format(i + 1, (
                                        self.dim - self.dim % 2) / 2 + self.dim % 2 * ((i + 1) % 2) - 1))
                        conn.append(("block_{}_{}:out2".format(i + 1, (self.dim - self.dim % 2) / 2 + self.dim % 2 * (
                                    (i + 1) % 2) - 1),
                                     "block_{}_{}:in1".format(i, j), manhattan,
                                     {"bend_radius": self.bend_radius}))
                else:
                    if i != self.dim - 2:
                        offset = 0 if self.dim % 2 == 0 else 1
                        conn.append((
                            "block_{}_{}:out1".format(i, j), "block_{}_{}:in2".format(i + 1, j + offset), manhattan,
                            {"bend_radius": self.bend_radius}))
                        conn.append(
                            ("block_{}_{}:out2".format(i, j), "block_{}_{}:in1".format(i - 1, j + offset), manhattan,
                             {"bend_radius": self.bend_radius}))
        return conn

    def _default_external_port_names(self):
        epn = dict()
        for i in range(self.dim):
            if self.f_grating_io:
                epn["gr_in_{}:vertical_io".format(i)] = "in{}".format(i + 1)
                epn["gr_out_{}:vertical_io".format(i)] = "out{}".format(i + 1)
            else:
                epn[self._input_list[i]] = "in{}".format(i + 1)
                epn[self._output_list[i]] = "out{}".format(i + 1)
        return epn

    def _default_propagated_electrical_ports(self):
        pep = []
        for i in range(self.dim):
            n_units = (self.dim - self.dim % 2) / 2 + self.dim % 2 * (i % 2)
            for j in range(n_units):
                pep.append("block_{}_{}_mzi_arm1_elec1".format(i, j))
                pep.append("block_{}_{}_mzi_arm1_elec2".format(i, j))
                pep.append("block_{}_{}_mzi_arm2_elec1".format(i, j))
                pep.append("block_{}_{}_mzi_arm2_elec2".format(i, j))
                pep.append("block_{}_{}_ht_elec1".format(i, j))
                pep.append("block_{}_{}_ht_elec2".format(i, j))
        return pep
