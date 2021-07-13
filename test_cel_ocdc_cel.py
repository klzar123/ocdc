from cel_ocdc_cel import CelOCDCCel
#from routed_cel_ocdc_cel import RoutedCelOCDCCel


coc = CelOCDCCel()
coc.Layout().visualize(annotate=True)
#coc.Layout().write_gdsii('CelOCDCCel.gds')


#rcoc = RoutedCelOCDCCel()
#rcoc.Layout().visualize()
#rcoc.Layout().write_gdsii('CelOCDCCel.gds')