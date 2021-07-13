from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, manhattan
from picazzo3.filters.mzi import MZIWithCells
from heatedwaveguide import HeatedWaveguide
from picazzo3.wg.dircoup import BendDirectionalCoupler
import re
from functools import partial

class PhMZI(CircuitCell):

    def _default_child_cells(self):
        child_cells = dict()
        split = pdk.M2X2_TE_1550()
        #split = BendDirectionalCoupler(name="bdc")
        ht = HeatedWaveguide(heater_width=5,
                             heater_offset=3.0,
                             m1_width=10.0,
                             m1_length=50.0)
        child_cells["mzi"] = MZIWithCells(name="my_mzi_cells_1",
                   splitter=split,
                   combiner=split,
                   arm2_contents=ht,
                   arm2_contents_port_names=["in", "out"])

        child_cells["ht"] = ht
        return child_cells

    def _default_connectors(self):
        mzi_len = self.child_cells["mzi"].get_default_view(i3.LayoutView).size_info().east
        arm2_elec1_pos = None
        for port in self.child_cells["mzi"].Layout().ports:
            if re.search("arm2_elec1", port.name):
                arm2_elec1_pos = port.position
        c = partial(manhattan, control_points=[(mzi_len + 20, 1.5),
                                               (mzi_len + 20, 2 * arm2_elec1_pos.y),
                                               (arm2_elec1_pos.x - 30, 2 * arm2_elec1_pos.y),
                                               (arm2_elec1_pos.x - 30, arm2_elec1_pos.y + 2 * arm2_elec1_pos.y)])
        return [("mzi:combiner_out1", "ht:in", c, {"bend_radius": 5.0})]

    def _default_place_specs(self):
        ht_pos_x = 0
        ht_pos_y = 0
        arm2_elec1_pos = None
        for port in self.child_cells["mzi"].Layout().ports:
            if re.search("arm2_elec1", port.name):
                arm2_elec1_pos = port.position
        ht_pos_x = arm2_elec1_pos.x - 25
        ht_pos_y = arm2_elec1_pos.y + 2 * arm2_elec1_pos.y
        return [i3.Place("mzi", (0, 0)),
                i3.Place("ht",(ht_pos_x, ht_pos_y))]

    def _default_external_port_names(self):
        return {"mzi:splitter_in1":"in1",
                "mzi:splitter_in2":"in2",
                "ht:out":"out1",
                "mzi:combiner_out2":"out2",
                "mzi:arm2_elec1":"mzi_arm2_elec1",
                "mzi:arm2_elec2":"mzi_arm2_elec2",
                "ht:elec1":"ht_elec1",
                "ht:elec2":"ht_elec2"}

    def _default_propagated_electrical_ports(self):
        return ["mzi_arm2_elec1", "mzi_arm2_elec2", "ht_elec1", "ht_elec2"]


