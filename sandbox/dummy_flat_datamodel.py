from atopile.model2.datamodel_flat import Link, Instance
import atopile.model2.datamodel as dm1

## Pin 1
dm1_p1 = dm1.Object(
    supers_refs=dm1.PIN)

dmf_p1 = Instance(
    path=('vdiv.ato','Vdiv','r1','p1'),
    class_= dm1_p1,
)
## Pin 2
dm1_p2 = dm1.Object(
    supers_refs=dm1.PIN)

dmf_p2 = Instance(
    path=('vdiv.ato','Vdiv','r1','p2'),
    class_= dm1_p2,
)
## Pin 1
dm1_s1 = dm1.Object(
    supers_refs=dm1.PIN)

dmf_s1 = Instance(
    path=('vdiv.ato','Vdiv','r1','s1'),
    class_= dm1_s1,
)
## Pin 2
dm1_s2 = dm1.Object(
    supers_refs=dm1.PIN)

dmf_s2 = Instance(
    path=('vdiv.ato','Vdiv','r1','s2'),
    class_= dm1_s2,
)

Resistor = dm1.Object()

r1 = Instance(
    path=('vdiv.ato','Vdiv','r1'),
    class_= Resistor,
    children

)


Vdiv = Instance(
    path=('vdiv.ato','Vdiv'),
    class_= dm1.Object()

)