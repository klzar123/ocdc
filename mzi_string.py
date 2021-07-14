from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, bezier_sbend
from picazzo3.filters.mzi import MZIWithCells
from heatedwaveguide import HeatedWaveguide

class MZIString(CircuitCell):
    _name_prefix = "MZI_String"
    mzi = i3.ChildCellProperty(doc="MZI")
    mzi_nums = i3.IntProperty(default=2, doc="Number of MZIs")
    spacing = i3.PositiveNumberProperty(default=500, doc="spacing between MZIs")
    # maybe useless, how to connect directly?
    bend_radius = i3.PositiveNumberProperty(default=30.0, doc="Bend radius of the connecting waveguides")

    def _default_mzi(self):
        split = pdk.M2X2_TE_1550()
        ht = HeatedWaveguide(heater_width=4,
                             heater_offset=3.0,
                             m1_width=10.0,
                             m1_length=50.0)
        return MZIWithCells(name="my_mzi_cells_1",
                   splitter=split,
                   combiner=split,
                   arm1_contents=ht,
                   arm1_contents_port_names=["in", "out"],
                   arm2_contents=ht,
                   arm2_contents_port_names=["in", "out"],)

    def _default_child_cells(self):
        child_cells = dict()
        for i in range(self.mzi_nums):
            child_cells["mzi_{}".format(i)] = self.mzi
        return child_cells

    def _default_connectors(self):
        conn = []
        for i in range(self.mzi_nums - 1):
            in_port = "mzi_{}:combiner_out1".format(i)
            out_port = "mzi_{}:splitter_in1".format(i+1)
            conn.append((in_port, out_port, bezier_sbend, {"bend_radius": self.bend_radius}))
        return conn

    def _default_place_specs(self):
        place_specs = []
        spacing = self.spacing
        for i in range(self.mzi_nums):
            y_cord = 0
            x_cord = i * spacing
            place_specs.append(i3.Place("mzi_{}".format(i), (x_cord, y_cord)))
        return place_specs

    def _default_external_port_names(self):
        epn = dict()
        epn["mzi_0:splitter_in1"]="in"
        epn["mzi_{}:combiner_out1".format(self.mzi_nums - 1)] = "out"
        # the electrical out ports
        for i in range(self.mzi_nums):
            epn["mzi_{}:arm1_elec1".format(i)] = "mzi_{}_arm1_elec1".format(i)
            epn["mzi_{}:arm1_elec2".format(i)] = "mzi_{}_arm1_elec2".format(i)
            epn["mzi_{}:arm2_elec1".format(i)] = "mzi_{}_arm2_elec1".format(i)
            epn["mzi_{}:arm2_elec2".format(i)] = "mzi_{}_arm2_elec2".format(i)
        return epn

    def _default_propagated_electrical_ports(self):
        pep = []
        for i in range(self.mzi_nums):
            pep.append("mzi_{}_arm1_elec1".format(i))
            pep.append("mzi_{}_arm1_elec2".format(i))
            pep.append("mzi_{}_arm2_elec1".format(i))
            pep.append("mzi_{}_arm2_elec2".format(i))
        return pep
