from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, bezier_sbend
from splittertree import SplitterTree
from mzi_string import MZIString
from heatedwaveguide import HeatedWaveguide

class OCDC(CircuitCell):
    _name_prefix = "OCDC"
    # Splitter Tree options
    splitter_tree = i3.ChildCellProperty(doc="SplitterTree used")
    levels = i3.IntProperty(default=3, doc="Number of levels")
    spacing_x = i3.PositiveNumberProperty(default=150.0, doc="Horizontal spacing between the levels")
    spacing_y = i3.PositiveNumberProperty(default=50.0, doc="Vertical spacing between the MMIs in the last level")
    bend_radius = i3.PositiveNumberProperty(default=5.0, doc="Bend radius of the connecting waveguides")

    # MZI options
    mzi_string = i3.ChildCellProperty(doc="MZI used")
    mzi_nums = i3.IntProperty(default=3, doc="Number of MZIs")
    mzi_spacing = i3.PositiveNumberProperty(default=500, doc="Spacing between MZIs")

    # Heater
    heated_wg = i3.ChildCellProperty(doc="Heated Waveguide")

    def get_n_rows(self):
        return 2 ** (self.levels - 1)

    def get_mzi_nums(self):
        return self.mzi_nums

    def _default_splitter_tree(self):
        splitter = pdk.M1X2_TE_1550()
        return SplitterTree(splitter=splitter,
                            levels=self.levels,
                            spacing_x=self.spacing_x,
                            spacing_y=self.spacing_y,
                            bend_radius=self.bend_radius)

    def _default_mzi_string(self):
        return MZIString(mzi_nums=self.mzi_nums, spacing=self.mzi_spacing)

    def _default_heated_wg(self):
        return HeatedWaveguide(heater_width=5,
                             heater_offset=3.0,
                             m1_width=10.0,
                             m1_length=50.0)
    def _default_child_cells(self):
        child_cells = dict()
        child_cells["splitter"] = self.splitter_tree
        child_cells["combiner"] = self.splitter_tree
        mzi_string_nums = 2 ** (self.levels - 1) - 1
        for i in range(mzi_string_nums):
            child_cells["mzis_{}".format(i)] = self.mzi_string
            child_cells["ht_wg_{}".format(i)] = self.heated_wg
        child_cells["ht_wg_{}".format(mzi_string_nums)] = self.heated_wg
        return child_cells

    def _default_connectors(self):
        conn = []
        max_port_idx = 2 ** self.levels
        # 1st out of splitter - heater - 1st in of combiner
        conn.append(("splitter:out_{}".format(max_port_idx), "ht_wg_{}:in".format(2 ** (self.levels - 1) - 1),
                     bezier_sbend, {"bend_radius": self.bend_radius}))
        conn.append(("ht_wg_{}:out".format(2 ** (self.levels - 1) - 1), "combiner:out_{}".format(max_port_idx),
                     bezier_sbend, {"bend_radius": self.bend_radius}))
        # connect the splitter - mzi_string - combinner
        mzi_string_nums = 2 ** (self.levels - 1) - 1
        for i in range(mzi_string_nums):
            # splitter - mzi_string
            conn.append(("splitter:out_{}".format(2 * (i + 1)), "mzis_{}:in".format(i),
                         bezier_sbend, {"bend_radius": self.bend_radius}))
            # mzi_string - heated_waveguide
            conn.append(("mzis_{}:out".format(i), "ht_wg_{}:in".format(i),
                         bezier_sbend, {"bend_radius": self.bend_radius}))
            # heated_waveguide - combiner
            conn.append(("ht_wg_{}:out".format(i), "combiner:out_{}".format(2 * (i + 1)),
                         bezier_sbend, {"bend_radius": self.bend_radius}))
        return conn

    def _default_place_specs(self):
        place_specs = []
        #these vars can be written into the class MZIString and splitter tree, later
        mzi_string_len = self.mzi_nums * self.mzi_spacing
        splitter_len = self.spacing_x * self.levels
        #place the combiner
        place_specs.append(i3.Place("combiner", (splitter_len * 2 + mzi_string_len + self.spacing_x, 0)))
        place_specs.append(i3.FlipH("combiner"))
        # place the mzi_string
        mzi_string_nums = 2 ** (self.levels - 1) - 1
        y_0 = - 0.5 * self.spacing_y * 2 ** (self.levels - 1)
        x_coord = splitter_len
        ht_x_coord = splitter_len + mzi_string_len + self.spacing_x / 2
        for i in range(mzi_string_nums):
            y_coord = y_0 + (i + 0.5) * self.spacing_y
            place_specs.append(i3.Place("mzis_{}".format(i),
                                        (x_coord, y_coord)))
            place_specs.append(i3.Place("ht_wg_{}".format(i), (ht_x_coord, y_coord)))
        y_coord = y_0 + (mzi_string_nums + 0.5) * self.spacing_y
        place_specs.append(i3.Place("ht_wg_{}".format(mzi_string_nums), (ht_x_coord, y_coord)))
        return place_specs

    def _default_external_port_names(self):
        epn = dict()
        epn["splitter:in"] = "in"
        epn["combiner:in"] = "out"
        # electrical out port of heater in mzi string
        mzi_string_nums = 2 ** (self.levels - 1) - 1
        for i in range(mzi_string_nums):
            for j in range(self.mzi_nums):
                epn["mzis_{}:mzi_{}_arm1_elec1".format(i, j)] = "mzi_{}_{}_arm1_elec1".format(i, j)
                epn["mzis_{}:mzi_{}_arm1_elec2".format(i, j)] = "mzi_{}_{}_arm1_elec2".format(i, j)
                epn["mzis_{}:mzi_{}_arm2_elec1".format(i, j)] = "mzi_{}_{}_arm2_elec1".format(i, j)
                epn["mzis_{}:mzi_{}_arm2_elec2".format(i, j)] = "mzi_{}_{}_arm2_elec2".format(i, j)
            epn["ht_wg_{}:elec1".format(i)] = "ht_wg_{}_elec1".format(i)
            epn["ht_wg_{}:elec2".format(i)] = "ht_wg_{}_elec2".format(i)
        epn["ht_wg_{}:elec1".format(mzi_string_nums)] = "ht_wg_{}_elec1".format(mzi_string_nums)
        epn["ht_wg_{}:elec2".format(mzi_string_nums)] = "ht_wg_{}_elec2".format(mzi_string_nums)
        return epn

    def _default_propagated_electrical_ports(self):
        pep = []
        # the independent heater
        mzi_string_nums = 2 ** (self.levels - 1) - 1
        for i in range(mzi_string_nums):
            for j in range(self.mzi_nums):
                pep.append("mzi_{}_{}_arm1_elec1".format(i,j))
                pep.append("mzi_{}_{}_arm1_elec2".format(i, j))
                pep.append("mzi_{}_{}_arm2_elec1".format(i, j))
                pep.append("mzi_{}_{}_arm2_elec2".format(i, j))
            pep.append("ht_wg_{}_elec1".format(i))
            pep.append("ht_wg_{}_elec2".format(i))
        pep.append("ht_wg_{}_elec1".format(mzi_string_nums))
        pep.append("ht_wg_{}_elec2".format(mzi_string_nums))
        return pep





