from pulp import *
import pandas as pd


# LECTURA DE DATOS
costes_df = pd.read_excel('241204_costes.xlsx')
operaciones_df = pd.read_excel('241204_datos_operaciones_programadas.xlsx')

# FILTRADO DE DATOS
# Operaciones filtradas con sus datos
operaciones_filtradas = operaciones_df[operaciones_df['Especialidad quirúrgica'] == 'Cardiología Pediátrica']
# Códigos de las operaciones filtradas
operaciones = operaciones_filtradas['Código operación'].tolist()
# Lista de los quirófanos
quirofanos = costes_df['Unnamed: 0'].tolist()
# Poner la primera columna como índice
costes_df.set_index('Unnamed: 0', inplace=True)

# OPERACIONES INCOMPATIBLES
incompatibilidades = {}
for i, op1 in operaciones_filtradas.iterrows():
    incompatibilidades[op1['Código operación']] = [
        op2['Código operación']
        for h, op2 in operaciones_filtradas.iterrows()
        if op2['Hora inicio '] < op1['Hora fin'] and op2['Hora fin'] > op1['Hora inicio '] 
        and op2['Código operación'] != op1['Código operación']] # No sea incompatible consigo misma


# MODELO
modelo = LpProblem('Modelo 1', sense = LpMinimize)

# Variables
x = LpVariable.dicts('x', [(i,j) for i in operaciones for j in quirofanos], cat = 'Binary')

# Función Objetivo
modelo += lpSum(costes_df.loc[j, i] * x[(i, j)] for i in operaciones for j in quirofanos)

# Restricciones
for i in operaciones:
    modelo += lpSum(x[(i,j)] for j in quirofanos) >= 1

for i in operaciones:
    for j in quirofanos:
        modelo += lpSum(x[(h,j)] for h in incompatibilidades[i])+x[(i,j)] <= 1
        
# Resolver el modelo
modelo.solve()

# Verificar el estado de la solución
print("Estado del modelo:", LpStatus[modelo.status])

# Imprimir operaciones con su quirófano asignado
for var in modelo.variables():
    if var.varValue > 0:
        print(var.name, "=", var.varValue)

# Imprimir el valor óptimo de la función objetivo
print("Coste total óptimo:", value(modelo.objective))





        

