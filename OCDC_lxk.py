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

# Part0-Grating
grating = pdk.GC_TE_1550()
grating_lo = grating.Layout()
grating_lo.visualize(annotate=True)

# PartI-SPtree
splitter = pdk.M1X2_TE_1550()
splitter_lv = splitter.Layout()
# splitter_lv.visualize(annotate=True)
splitter_cm = splitter.CircuitModel()

Spt_y = 100.0
Spt = SplitterTree(levels=2, splitter=splitter, spacing_y= Spt_y)
Spt_lv = Spt.Layout()
Spt_cm = Spt.CircuitModel()
#Spt_lv.visualize(annotate=True)
# my_circuit_lv.write_gdsii("splitter_tree.gds")

# PratII-mzi
split = pdk.M2X2_TE_1550()
split.Layout().visualize(annotate=False)
# heater def
ht = HeatedWaveguide(heater_width=1,
                     heater_offset=3.0,
                     m1_width=5.0,
                     m1_length=5.0)
ht_lv = ht.Layout(shape=[(0.0, 0), (40.0, 0)])
#ht_lv.visualize(annotate=True)

# mzi def
mzi = MZIWithCells(name="my_mzi_cells_1",
                   splitter=split,
                   combiner=split,
                   arm1_contents=ht,
                   arm1_contents_port_names=["in", "out"],
                   arm2_contents=ht,
                   arm2_contents_port_names=["in", "out"],
                   )
mzi_lo = mzi.Layout(extra_length=-10.)
mzi_lo.visualize(annotate=True)
# print mzi_lo.size_info()

# PartIII-MZI string
cells = {"mzi1": mzi,
         "mzi2": mzi,
         # "template": pdk.TEMPLATE_BLOCK()
         }
links = [("mzi1:combiner_out1", "mzi2:splitter_in1")
         ]
spacing_x = 400.0
spacing_y = 0.0

trans = {  # "template": (0, 0),
    "mzi1": (0, 0),
    "mzi2": (spacing_x, spacing_y)
}

external_port_names = {"mzi1:splitter_in1": "in1",
                       "mzi1:splitter_in2": "in2",
                       "mzi2:splitter_out1": "out1",
                       "mzi2:splitter_out2": "out2",}

wg_tt = pdk.SWG450_CTE()

# Create the PCell
mzi_string = PlaceAndAutoRoute(child_cells=cells,
                               links=links,
                               trace_template=wg_tt)
mzi_string_layout = mzi_string.Layout(child_transformations=trans)
mzi_string_layout.visualize(annotate=True)

# PartIV-total circuit
# PlaceAndAutoRoute
cells = {"gc_in": grating,
         "mzi_s1": mzi_string,
         "mzi_s2": mzi_string,
         "mzi_s3": mzi_string,
         "splitter": Spt,
         "combiner": Spt,
         "gc_out": grating
         # "template": pdk.TEMPLATE_BLOCK()
         }

links = [  # input coupler to splitter tree
    ("gc_in:wg", "splitter:in"),

    # output coupler to splitter tree
    ("gc_out:wg", "combiner:in"),

    # connecting the mzi_string to splitter
    ("mzi_s1:mzi1_splitter_in2", "splitter:out_2"),
    ("mzi_s2:mzi1_splitter_in2", "splitter:out_1"),
    ("mzi_s3:mzi1_splitter_in2", "splitter:out_3"),

    # connecting the mzi_string to splitter
    ("mzi_s1:mzi2_combiner_out2", "combiner:out_2"),
    ("mzi_s2:mzi2_combiner_out2", "combiner:out_1"),
    ("mzi_s3:mzi2_combiner_out2", "combiner:out_3"),

    # connecting reference
    ("splitter:out_4", "combiner:out_4")
]

# Create the PCell
my_circuit = PlaceAndAutoRoute(child_cells=cells,
                               links=links,
                               trace_template=wg_tt)

d = 150.0

# Align the outports of the the rings

transf = {"gc_in": (-d , 0),
          "splitter": (0.0 , 0),
          "combiner": i3.HMirror() + i3.Translation((10 * d, -0*d)),
          "gc_out": i3.HMirror() + i3.Translation((11 * d, -0*d)),
          "mzi_s1": (3 * d,-d),
          "mzi_s2": (3 * d,0),
          "mzi_s3": (3 * d,d),
          }


# Create Layout
layout = my_circuit.Layout(child_transformations=transf)
layout.visualize(annotate=True)

layout.visualize_2d()
layout.write_gdsii('OCDC.gds')
