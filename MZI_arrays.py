import CSiP180Al.all as pdk
from picazzo3.filters.mzi import MZIWithCells
from picazzo3.wg.dircoup import BendDirectionalCoupler
from heatedwaveguide import HeatedWaveguide
from picazzo3.routing.place_route import PlaceAndAutoRoute

split = BendDirectionalCoupler(name="my_splitter_7")
split.Layout(bend_angle=30.0)

ht = HeatedWaveguide(heater_width=0.6,
                     heater_offset=1.0,
                     m1_width=1.0,
                     m1_length=3.0)
ht_lv = ht.Layout(shape=[(0.0, 0.0), (20.0, 0.0)])
# ht_lv.visualize(annotate=True)

mzi = MZIWithCells(name="my_mzi_cells_1",
                   splitter=split,
                   combiner=split,
                   arm1_contents=ht,
                   arm1_contents_port_names=["in", "out"],
                   )
mzi_lo = mzi.Layout(extra_length=0)

mzi_lo.visualize(annotate=True)

spacing_x = 125.
spacing_y = 150.
n_column = 7
n_row = 4
cells = {}
links = []
trans = {}
wg_tt = pdk.SWG450_CTE()

for i in range(n_column):
    if i % 2 == 0:
        n_mzi = n_row
    elif i % 2 == 1:
        n_mzi = n_row - 1
    for mz in range(n_mzi):
        cells["mzi_{}_{}".format(i, mz)] = mzi
        if i % 2 == 0 and i == n_column - 1:
            trans["mzi_{}_{}".format(i, mz)] = (i * spacing_x, mz * spacing_y)
        # elif i % 2 == 0 and i == n_column - 2:
        #     links.append(("mzi_{}_{}:combiner_out1".format(i, n_mzi - 2), "mzi_{}_{}:splitter_in2".format(i + 1, n_mzi - 2)))
        #     links.append(("mzi_{}_{}:combiner_out2".format(i, 0), "mzi_{}_{}:splitter_in1".format(i + 1, 0)))
        #
        # elif i % 2 == 1 and i == n_column - 2:
        #     pass

        # elif i % 2 == 0 and mz == 0 and i != n_column - 2:
        elif i % 2 == 0 and mz == 0:
            links.append(("mzi_{}_{}:combiner_out1".format(i, mz), "mzi_{}_{}:splitter_in1".format(i + 2, mz)))
            links.append(("mzi_{}_{}:combiner_out2".format(i, mz), "mzi_{}_{}:splitter_in1".format(i + 1, mz)))
            trans["mzi_{}_{}".format(i, mz)] = (i * spacing_x, 0)
        # elif i % 2 == 0 and mz == n_mzi - 1 and i != n_column - 2:
        elif i % 2 == 0 and mz == n_mzi - 1:
            links.append(("mzi_{}_{}:combiner_out1".format(i, mz), "mzi_{}_{}:splitter_in2".format(i + 1, mz - 1)))
            links.append(("mzi_{}_{}:combiner_out2".format(i, mz), "mzi_{}_{}:splitter_in2".format(i + 2, mz)))
            trans["mzi_{}_{}".format(i, mz)] = (i * spacing_x, mz * spacing_y)
        elif i % 2 == 0:
            links.append(("mzi_{}_{}:combiner_out1".format(i, mz), "mzi_{}_{}:splitter_in2".format(i + 1, mz - 1)))
            links.append(("mzi_{}_{}:combiner_out2".format(i, mz), "mzi_{}_{}:splitter_in1".format(i + 1, mz)))
            trans["mzi_{}_{}".format(i, mz)] = (i * spacing_x, mz * spacing_y)
        elif i % 2 == 1:
            links.append(("mzi_{}_{}:combiner_out1".format(i, mz), "mzi_{}_{}:splitter_in2".format(i + 1, mz)))
            links.append(("mzi_{}_{}:combiner_out2".format(i, mz), "mzi_{}_{}:splitter_in1".format(i + 1, mz + 1)))
            trans["mzi_{}_{}".format(i, mz)] = (i * spacing_x, mz * spacing_y + 0.5 * spacing_y)


# Create the PCell
my_circuit = PlaceAndAutoRoute(child_cells=cells,
                               links=links,
                               trace_template=wg_tt)

# Create Layout
layout = my_circuit.Layout(child_transformations=trans)

layout.visualize()
layout.write_gdsii('array_circuit.gds')
