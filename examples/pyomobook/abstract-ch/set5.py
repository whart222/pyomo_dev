import pyomo.environ as pyo

model = pyo.AbstractModel()

# @decl:
model.A = pyo.Set(dimen=4)
# @:decl

instance = model.create_instance('set5.dat')


for tpl in sorted(list(instance.A.data()), key=lambda x: tuple(map(str, x))):
    print(tpl)
