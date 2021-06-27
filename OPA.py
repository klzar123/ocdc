from si_fab import all as pdk
from ipkiss3 import all as i3
from circuit.all import CircuitCell, manhattan
from pteam_library_si_fab import all as pt_lib

class OPA(CircuitCell):
    """Class for an optical phased array (OPA) composed of a splitter tree and an array of heaters.
    """
    heater = i3.ChildCellProperty(doc="Heater PCell used at the outputs of the splitter tree")
    splitter = i3.ChildCellProperty(doc="Splitter PCell used in the splitter tree")
    levels = i3.PositiveIntProperty(default=4, doc="Number of levels in the splitter tree")
    spacing_y = i3.PositiveNumberProperty(default=50.0,
                                          doc="Horizontal spacing between the levels of the splitter tree")
    spacing_x = i3.PositiveNumberProperty(default=100.0,
                                          doc="Vertical spacing between the splitters in the last level")

    def _get_n_outputs(self):
        return 2**self.levels

    def _default_heater(self):
        # By default, the heater is a 1 mm-long heated waveguide
        ht = pdk.HeatedWaveguide()
        ht.Layout(shape=[(0.0, 0.0), (1000.0, 0.0)])
        return ht

    def _default_splitter(self):
        return pdk.MMI1x2Optimized()

    def _default_child_cells(self):
        child_cells = dict()
        # Create a splitter tree, then add a heater at each output
        splitter_tree = pt_lib.SplitterTree(
            levels=self.levels,
            splitter=self.splitter,
            spacing_y=2 * self.spacing_y,
        )
        child_cells["tree"] = splitter_tree
        for cnt in range(self._get_n_outputs()):
            child_cells["ht{}".format(cnt)] = self.heater
        return child_cells

    def _default_place_specs(self):
        # Provides positions in which the heaters will be placed with respect to the splitter tree
        specs = []
        east = self.child_cells["tree"].get_default_view(i3.LayoutView).size_info().east

        for cnt in range(self._get_n_outputs()):
            specs.append(
                i3.Place(
                    "ht{}".format(cnt),
                    (east + self.spacing_x, (cnt - (self._get_n_outputs() - 1) / 2.0) * self.spacing_y)
                )
            )
        return specs

    def _default_connectors(self):
        return [("ht{}:in".format(cnt), "tree:out{}".format(cnt + 1), manhattan) for cnt in range(2**self.levels)]

    def _default_propagated_electrical_ports(self):
        # Propagate the electrical ports of each individual heaters so that they appear as ports of the CircuitCell
        pep = []
        for cnt in range(self._get_n_outputs()):
            pep.append("hti{}".format(cnt))
            pep.append("hto{}".format(cnt))
        return pep

    def _default_external_port_names(self):
        # Here the names of the electrical ports are set
        epn = dict()
        epn["tree:in"] = "in"
        for cnt in range(self._get_n_outputs()):
            epn["ht{}:elec1".format(cnt)] = "hti{}".format(cnt)
            epn["ht{}:elec2".format(cnt)] = "hto{}".format(cnt)
            epn["ht{}:out".format(cnt)] = "out{}".format(cnt)
        return epn

if __name__ == "__main__":
    heater = pdk.HeatedWaveguide(name="heated_wav")
    heater.Layout(shape=[(0, 0), (1000.0, 0.0)])
    opa = OPA(name="opa_array", heater=heater, levels=3)
    opa.Layout().visualize(annotate=True)