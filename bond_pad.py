import CSiP180Al.all as pdk
from ipkiss3 import all as i3
from picazzo3.routing.place_route import PlaceComponents
from ipkiss3.pcell.routing import RouteManhattan
from ipkiss3.pcell.wiring import ElectricalPort, ElectricalWire, ElectricalWireTemplate

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

if __name__ == "__main__":
    bp = BondPad()
    bp.Layout().visualize()