from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, bezier_sbend
from picazzo3.filters.mzi import MZIWithCells
from heatedwaveguide import HeatedWaveguide
from picazzo3.wg.dircoup import BendDirectionalCoupler

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
        return [("mzi:combiner_out1", "ht:in", bezier_sbend, {"bend_radius": 5.0})]

    def _default_place_specs(self):
        return [i3.Place("mzi", (0, 0)), i3.Place("ht", (500, 10))]

    def _default_external_port_names(self):
        return {"mzi:splitter_in1":"in1",
                "mzi:splitter_in2":"in2",
                "ht:out":"out1",
                "mzi:combiner_out2":"out2"}


