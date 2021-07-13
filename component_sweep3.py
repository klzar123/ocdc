from demolib import technology
from demolib.components.ring.cell import HeatedDropRingAtWavelength
from routing.apac import APAC, get_port_from_interface
from routing.routing_functions import bezier_sbend
from demolib.components.grating_couplers import FC_TE_1550
from demolib.components.metal.bondpad.cell import BONDPAD_5050
import numpy as np
from ipkiss3 import all as i3
wavs = np.linspace(1.5, 1.6, 10)


def get_electrical_route_elements(lv):
    elems = i3.ElementList()
    insts = lv.instances
    delta = 0
    sep = 10
    x_second = insts["gr_out1_0_1"].size_info().east + 10
    x_first = insts["gr_out1_0_0"].size_info().east + 10
    for cnt, (l1, l2) in enumerate(lv.electrical_links):
        p1 = get_port_from_interface(l1, insts)
        p2 = get_port_from_interface(l2, insts)
        routeline = [p1, p2]
        if p1.name == "el_in":
            ss = 4 * sep
        else:
            ss = 3 * sep
        first_points = [(p1.x, p1.y - ss), (p1.x + 100, p1.y - ss)]
        if cnt > len(wavs) * 2:
            delta -= sep
        else:
            delta += sep
        col = l1[4]  # extract the column from the label :-)
        if col == '1':
            extra_points = [(x_second + delta, p1.y - ss)]
        else:
            extra_points = [(x_first + ss, p1.y - ss), (x_first + ss, p1.y - ss + 100),
                            (x_second + delta, p1.y - ss + 100)]
        all_points = first_points + extra_points
        route = [p1] + all_points + [(all_points[-1][0], p2.y), (p2.x - 50, p2.y)] + [p2]
        elems += i3.Path(layer=i3.TECH.PPLAYER.M1, line_width=5.0, shape=route)
    return elems


class TopCell(APAC):
    grating_sep = i3.PositiveNumberProperty(default=75.0)
    col_spacing = i3.PositiveNumberProperty(default=500)
    bp_sep = i3.PositiveNumberProperty(default=100.0)

    def _default_child_cells(self):
        childs = {}
        gr = FC_TE_1550()
        bp = BONDPAD_5050()
        for cnt, w in enumerate(wavs):
            c = HeatedDropRingAtWavelength(res_wavelength=w)
            for col in range(2):

                childs["r_{}_{}".format(cnt, col)] = c
                childs["gr_in1_{}_{}".format(cnt, col)] = gr
                childs["gr_out1_{}_{}".format(cnt, col)] = gr
                childs["gr_in2_{}_{}".format(cnt, col)] = gr
                childs["gr_out2_{}_{}".format(cnt, col)] = gr
                childs["bp_elec1_{}_{}".format(cnt, col)] = bp
                childs["bp_elec2_{}_{}".format(cnt, col)] = bp

        return childs

    def _default_electrical_links(self):
        in_labels = []
        out_labels = []
        insts = self.get_child_instances()

        for cnt, w in enumerate(wavs):
            for col in [1, 0]:
                in_labels.extend(["r_{}_{}:el_in".format(cnt, col), "r_{}_{}:el_out".format(cnt, col)])
                out_labels.extend(["bp_elec2_{}_{}:m1".format(cnt, col), "bp_elec1_{}_{}:m1".format(cnt, col)])

        return [(a, b) for (a, b) in zip(in_labels, out_labels)]

    def _default_connectors(self):
        conn = []
        for col in range(2):
            for cnt, w in enumerate(wavs):
                for cnt2 in [1, 2]:
                    p1 = "gr_in{}_{}_{}:out".format(cnt2, cnt, col)
                    p2 = "r_{}_{}:in{}".format(cnt, col, cnt2)
                    conn.append((p1, p2, bezier_sbend))

                    p1 = "gr_out{}_{}_{}:out".format(cnt2, cnt, col)
                    p2 = "r_{}_{}:out{}".format(cnt, col, cnt2)
                    conn.append((p1, p2, bezier_sbend))

        return conn

    def _default_specs(self):

        n_rings = len(wavs)
        specs = []
        for cnt, w in enumerate(wavs):
            for col in range(2):
                specs += [
                    i3.Place("r_{}_{}".format(cnt, col),(200 + col * self.col_spacing, 2 * cnt * self.grating_sep)),
                    i3.Place("gr_in1_{}_{}".format(cnt, col), (0, 2 * cnt * self.grating_sep)),
                    i3.Place("gr_out1_{}_{}".format(cnt, col), (400 + col * self.col_spacing, 2 * cnt * self.grating_sep), 180),
                    i3.Place("gr_out2_{}_{}".format(cnt, col), (col * self.col_spacing, (2 * cnt + 1) * self.grating_sep)),
                    i3.Place("gr_in2_{}_{}".format(cnt, col), (400 + col * self.col_spacing, (2 * cnt + 1) * self.grating_sep), 180)]
                bp_row = 2 * cnt + (1 - col)
                specs += [
                    i3.Place("bp_elec1_{}_{}".format(cnt, col), (1200,500+(bp_row-n_rings+0.5)* self.bp_sep+200)),
                    i3.Place("bp_elec2_{}_{}".format(cnt, col), (1300,500+(bp_row-n_rings+0)* self.bp_sep+200))]


        return specs

    class Layout(APAC.Layout):

        def _get_electrical_route_elements(self):
            return get_electrical_route_elements(self)


def get_top_lv():
    cell = TopCell(name="top_cell")
    lv = cell.Layout()
    return lv


if __name__ == "__main__":
    lv = get_top_lv()
    lv.write_gdsii("component_sweep3.gds")
