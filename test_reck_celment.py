import sys, os

sys.path.append(os.path.join(os.pardir, 'luceda_academy_35-120', 'SJTU_MZI_samples/additional_utils'))
sys.path.append("C:\CSiP180Al\ipkiss")

from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from reck import Reck
from celment import Celment
from PhMZI import PhMZI
from circuit.utils import get_port_from_interface
import re


#rk = Reck(levels=5)
#rk.Layout().visualize(annotate=False)

#phmzi = PhMZI()
#phmzi.Layout().visualize(annotate=False)

cel = Celment(dim=3)
cel.Layout().visualize(annotate=True)
#ports = cel.get_electric_ports()
ports = dict()
for port in cel.Layout().ports:
    if not re.search("in|out", port.name):
        ports[port.name] = port.position.x
o_ports = [k for k, v in sorted(ports.items(), key=lambda item: item[1])]
for name in o_ports:
    print(name)

