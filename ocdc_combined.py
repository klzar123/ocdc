import sys, os

sys.path.append(os.path.join(os.pardir, 'luceda_academy_35-120', 'SJTU_MZI_samples/additional_utils'))
sys.path.append("C:\CSiP180Al\ipkiss")

from CSiP180Al import all as pdk
from ipkiss3 import all as i3
# from circuit.all import CircuitCell, bezier_sbend
from splittertree import SplitterTree
from picazzo3.filters.mzi import MZIWithCells
from heatedwaveguide import HeatedWaveguide
from picazzo3.routing.place_route import PlaceAndAutoRoute

from routed_ocdc import  RoutedOCDC
from ocdc import OCDC

ocdc_4 = OCDC(levels=4, mzi_nums=2)
ocdc_5 = OCDC(levels=5, mzi_nums=2)

rocdc_4 = RoutedOCDC(dut=ocdc_4)
rocdc_5 = RoutedOCDC(dut=ocdc_5)

cells = {"rocdc1": rocdc_5,
         "rocdc2": rocdc_4,
         }
trans = {
    "rocdc1": (0, 1500),
    "rocdc2": (0, 3000)
}

com_rocdc = PlaceAndAutoRoute(child_cells=cells)
com_rocdc_layout = com_rocdc.Layout(child_transformations=trans)
com_rocdc_layout.visualize()
