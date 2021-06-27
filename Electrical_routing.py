import CSiP180Al.all as pdk
from ipkiss3 import all as i3
from picazzo3.routing.place_route import PlaceComponents
from ipkiss3.pcell.routing import RouteManhattan
from ipkiss3.pcell.wiring import ElectricalPort, ElectricalWire, ElectricalWireTemplate

input_port = ElectricalPort(name="in", position=(5.0, 5.0))
output_port = ElectricalPort(name="out", position=(20.0, 20.0))

# create the route object
route = RouteManhattan(input_port=input_port,
                       output_port=output_port,
                       angle_in=180.,
                       angle_out=0.
                       )

tpl = ElectricalWireTemplate()
tpl.Layout(layer=i3.TECH.PPLAYER.M1.DRW)
wire = ElectricalWire(trace_template=tpl)
layout = wire.Layout(shape=route)
layout.visualize(annotate=True)


class BondPad(i3.PCell):
    """
    Bondpad to be used here
    """
    class Layout(i3.LayoutView):
        size = i3.Size2Property(default=(50.0, 50.0), doc="Size of the bondpad")
        metal_layer = i3.LayerProperty(default=i3.TECH.PPLAYER.M1.DRW, doc="Metal used for the bondpad")

        def _generate_elements(self, elems):
            elems += i3.Rectangle(layer=self.metal_layer, box_size=self.size)
            return elems

        def _generate_ports(self, ports):
            ports += i3.ElectricalPort(name="m1", position=(0.0, 0.0), shape=self.size, process=self.metal_layer.process)
            return ports

bp = BondPad()
bp.Layout().visualize(annotate=True)

class ElectricalRoutingExample(PlaceComponents):
    bondpad = i3.ChildCellProperty(doc="Bondpad used")
    num_bondpads = i3.PositiveIntProperty(doc="Number of bondspads")

    def _default_num_bondpads(self):
        return 5

    def _default_bondpad(self):
        return BondPad()

    def _default_child_cells(self):
        childs = dict()
        for w in range(self.num_bondpads):
            childs["bp_north_{}".format(w)] = self.bondpad
            childs["bp_west_{}".format(w)] = self.bondpad

        return childs

    class Layout(PlaceComponents.Layout):

        bp_spacing = i3.PositiveNumberProperty(default=200.0, doc="Spacing between the bondpads")
        center_bp_north = i3.PositiveNumberProperty(doc="Center for the north bondpads")
        center_bp_west = i3.PositiveNumberProperty(doc="Center for the west bondpads")
        metal_width = i3.PositiveNumberProperty(doc="Metal width", default=5.0)

        def _default_center_bp_north(self):
            return 1000

        def _default_center_bp_west(self):
            return 100

        def _default_child_transformations(self):
            trans = dict()
            for w in range(self.num_bondpads):
                trans["bp_north_{}".format(w)] = i3.Rotation(rotation=90.0) + i3.Translation(translation=(
                self.center_bp_north + (w - self.num_bondpads / 2.0 + 0.5) * self.bp_spacing, 1000 - 100))
                trans["bp_west_{}".format(w)] = i3.Rotation(rotation=90.0) + i3.Translation(
                    translation=(0 - 100, self.center_bp_west - (w - self.num_bondpads / 2.0 + 0.5) * self.bp_spacing))

            return trans

        @i3.cache()
        def get_electrical_routes(self):
            routes = []
            trans = self.child_transformations
            for w in range(self.num_bondpads):
                p1 = self.bondpad.ports["m1"].transform_copy(transformation=trans["bp_north_{}".format(w)])
                p2 = self.bondpad.ports["m1"].transform_copy(transformation=trans["bp_west_{}".format(w)])
                r = i3.RouteManhattan(input_port=p1,
                                      output_port=p2,
                                      angle_out=180.0,
                                      angle_in=-90.0,
                                      rounding_algorithm=None)
                routes.append(r)

            return routes

        def _generate_instances(self, insts):
            insts = super(ElectricalRoutingExample.Layout, self)._generate_instances(insts)
            for r in self.get_electrical_routes():
                wire = ElectricalWire(trace_template=tpl)
                layout = wire.Layout(shape=r)
                insts += i3.SRef(layout)

            return insts


if __name__ == '__main__':
    lv = ElectricalRoutingExample().Layout()
    #lv.write_gdsii("electrical_routing_test.gds")
