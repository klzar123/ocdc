

#from mzi_string import MZIString
#from splittertree import SplitterTree
from CSiP180Al import all as pdk
#from picazzo3.filters.mzi import MZIWithCells
#from heatedwaveguide import HeatedWaveguide
#from ipkiss3 import all as i3
#import re
from ocdc import OCDC
from routed_ocdc import RoutedOCDC

#mzis = MZIString(mzi_nums=5)
#mzis.Layout().visualize(annotate=True)
#dut_lv=mzis.get_default_view(i3.LayoutView)
#port_list_out_sorted = [p.name for p in dut_lv.ports.y_sorted()]
#print(port_list_out_sorted)


ocdc = OCDC(levels=4, mzi_nums=3)
#ocdc.Layout().visualize(annotate=True)
#ocdc_lv = ocdc.get_default_view(i3.LayoutView)
#ocdc_port_list = [p.name for p in ocdc_lv.ports if re.search("elec", p.name)]
#for port in ocdc_port_list:
#    print port

r_ocdc = RoutedOCDC(dut=ocdc)
r_ocdc.Layout().visualize(annotate=False)

#split = pdk.M2X2_TE_1550()
#split.Layout().visualize(annotate=True)

"""
split = pdk.M2X2_TE_1550()
ht = HeatedWaveguide(heater_width=5,
                     heater_offset=3.0,
                     m1_width=10.0,
                     m1_length=50.0)
mzi=MZIWithCells(name="my_mzi_cells_1",
    splitter=split,
    combiner=split,
    arm1_contents=ht,
    arm1_contents_port_names=["in", "out"],
    arm2_contents=ht,
    arm2_contents_port_names=["in", "out"],)
dut_lv=mzi.get_default_view(i3.LayoutView)
port_list_out_sorted = [p.name for p in dut_lv.ports.y_sorted()]
print(port_list_out_sorted)
"""

""""
from technologies import silicon_photonics
from picazzo3.filters.mzi import MZIWithCells
from picazzo3.wg.dircoup import BendDirectionalCoupler
from picazzo3.filters.ring import RingRectNotchFilter
from ipkiss3 import all as i3

split = BendDirectionalCoupler(name="my_splitter_7")
split.Layout(bend_angle=30.0)

ring = RingRectNotchFilter(name="my_ring_8")

mzi = MZIWithCells(name="my_mzi_cells_1",
                           splitter=split,
                           combiner=split,
                           arm1_contents=ring,
                           arm1_contents_port_names=["in", "out"],
                           )
layout = mzi.Layout(extra_length=-50.0)
layout.visualize(annotate=True)
dut_lv=mzi.get_default_view(i3.LayoutView)
port_list_out_sorted = [p.name for p in dut_lv.ports.y_sorted()]
print(port_list_out_sorted)
"""