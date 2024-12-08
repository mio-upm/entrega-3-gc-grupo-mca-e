from pulp import *
import pandas as pd


# LECTURA DE DATOS
costes_df = pd.read_excel('241204_costes.xlsx')
operaciones_df = pd.read_excel('241204_datos_operaciones_programadas.xlsx')

# FILTRADO DE DATOS
# Operaciones filtradas con sus datos
operaciones_filtradas = operaciones_df[
    operaciones_df['Especialidad quirúrgica'].isin(
        ['Cardiología Pediátrica', 'Cirugía Cardiovascular', 'Cirugía Cardíaca Pediátrica', 'Cirugía General y del Aparato Digestivo'])]
# Códigos de las operaciones filtradas
operaciones = operaciones_filtradas['Código operación'].tolist()
# Poner la primera columna como índice
costes_df.set_index('Unnamed: 0', inplace=True)
# Lista de los quirófanos
quirofanos = costes_df.index.tolist()

# FUNCIONES
# Operaciones incompatibles
def son_incompatibles(operaciones): 
    incompatibilidades = {}
    for i, op1 in operaciones.iterrows():
        incompatibilidades[op1['Código operación']] = [op2['Código operación']
            for h, op2 in operaciones.iterrows()
            if op2['Hora inicio '] < op1['Hora fin'] and op2['Hora fin'] > op1['Hora inicio ']
            and op2['Código operación'] != op1['Código operación']]
    return incompatibilidades

# Generar planificaciones factibles
def generar_planificaciones(operaciones, incompatibilidades):
    planificaciones_orden_inicio = []
    planificaciones_orden_final = []

    # Función para asignar operaciones a planificaciones
    def asignar_planificaciones(operaciones, planificaciones):
        for op in operaciones['Código operación']:
            asignado = False
            # Intentar añadir la operación a una planificación existente
            for planificacion in planificaciones:
                if all(op not in incompatibilidades.get(existing_op, []) for existing_op in planificacion):
                    planificacion.append(op)
                    asignado = True
                    break
        
            # Si no se puede añadir, crear una nueva planificación
            if not asignado:
                planificaciones.append([op])

    # Asignar planificaciones recorriendo desde el principio
    asignar_planificaciones(operaciones, planificaciones_orden_inicio)

    # Asignar planificaciones recorriendo desde el final
    operaciones_reversed = operaciones.iloc[::-1]
    asignar_planificaciones(operaciones_reversed, planificaciones_orden_final)

    # Combinar las planificaciones generadas por ambos recorridos
    planificaciones_combinadas = planificaciones_orden_inicio + planificaciones_orden_final

    return planificaciones_combinadas

# MODELO
incompatibilidades = son_incompatibles(operaciones_filtradas)
planificaciones = generar_planificaciones(operaciones_filtradas, incompatibilidades)

modelo = LpProblem('Modelo 2', sense=LpMinimize)

# Parámetros
Ci = costes_df.mean().to_dict()

Bik = {}
for indx_planificacion, planificacion in enumerate(planificaciones):
    for _, operacion in operaciones_filtradas.iterrows():
        Bik[(operacion['Código operación'], indx_planificacion)] = 1 if operacion['Código operación'] in planificacion else 0

Ck = {}
for indx_planificacion, planificacion in enumerate(planificaciones):
    Ck[(indx_planificacion)] = lpSum(
        Bik[(operacion['Código operación'], indx_planificacion)]*Ci[operacion['Código operación']] 
        for _, operacion in operaciones_filtradas.iterrows())

# Variables
y = LpVariable.dicts('y', [(k) for k in range(len(planificaciones))], cat='Binary')

# Función Objetivo
modelo += lpSum(Ck[k] * y[(k)] for k in range(len(planificaciones)))

# Restricciones
for _, operacion in operaciones_filtradas.iterrows():
    modelo += lpSum(Bik[(operacion['Código operación'], k)] * y[k] for k in range(len(planificaciones))) >= 1

# Resolver el modelo
modelo.solve()

# Verificar el estado de la solución
print("\nEstado del modelo:", LpStatus[modelo.status])

# Imprimir las planificaciones seleccionadas con sus correspondientes operaciones
print("\nPlanificaciones seleccionadas con sus operaciones:")
for k in Ck.keys():
    if y[k].varValue > 0:
        print(f"Planificación {k}: {', '.join(planificaciones[k])}")
        
# Imprimir el valor óptimo de la función objetivo
print("\nCoste total mínimo:", value(modelo.objective))


