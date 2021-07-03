import sys, os

sys.path.append(os.path.join(os.pardir, 'luceda_academy_35-120', 'SJTU_MZI_samples/additional_utils'))
sys.path.append("C:\CSiP180Al\ipkiss")

from CSiP180Al import all as pdk
from ipkiss3 import all as i3
from reck import Reck
from celment import Celment
from PhMZI import PhMZI


#rk = Reck(levels=5)
#rk.Layout().visualize(annotate=False)

#phmzi = PhMZI()
#phmzi.Layout().visualize(annotate=True)

cel = Celment(rows=10, columns=6)
cel.Layout().visualize()