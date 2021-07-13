#from mzi_string import MZIString
#from splittertree import SplitterTree
from CSiP180Al import all as pdk
#from picazzo3.filters.mzi import MZIWithCells
#from heatedwaveguide import HeatedWaveguide
from ipkiss3 import all as i3
#import re
from ocdc import OCDC
from routed_ocdc import RoutedOCDC
from picazzo3.routing.place_route import PlaceAndAutoRoute


ocdc_1 = OCDC(levels=5, mzi_nums=2, spacing_x=250)
ocdc_2 = OCDC(levels=4, mzi_nums=2)
ocdc_3 = OCDC(levels=4, mzi_nums=2)
#ocdc.Layout().visualize(annotate=False)
#ocdc_lv = ocdc.get_default_view(i3.LayoutView)
#ocdc_port_list = [p.name for p in ocdc_lv.ports if re.search("elec", p.name)]
#for port in ocdc_port_list:
#    print port

# r_ocdc = RoutedOCDC(dut=ocdc_1)
# r_ocdc.Layout().visualize(annotate=False)
# r_ocdc.Layout().write_gdsii('OCDC.gds')

rocdc_1 = RoutedOCDC(dut=ocdc_1, layout_direction=1)
rocdc_2 = RoutedOCDC(dut=ocdc_2)
rocdc_3 = RoutedOCDC(dut=ocdc_3)

# PlaceAndAutoRoute
cells = {"group_1": rocdc_1,
         "group_2": rocdc_2,
         "group_3": rocdc_3,
         # "template": pdk.TEMPLATE_BLOCK()
         }

links = []

# Create the PCell
wg_tt = pdk.SWG450_CTE()
my_circuit = PlaceAndAutoRoute(child_cells=cells,
                               links=links,
                               trace_template=wg_tt)

d = 1000.0
r = 222.0

# Align the outports of the the rings

transf = {"group_1": (1 * d - r, 2 * d),
          "group_2": i3.VMirror() + i3.Translation((1 * d, 1 * d)),
          "group_3": (1 * d, 3 * d),
          }


# Create Layout
layout = my_circuit.Layout(child_transformations=transf)
layout.visualize(annotate=False)

# layout.visualize_2d()
# layout.write_gdsii('OCDC.gds')