from pulp import *
import pandas as pd
import random
import matplotlib.pyplot as plt

# LECTURA DE DATOS
costes_df = pd.read_excel('241204_costes.xlsx')
operaciones_df = pd.read_excel('241204_datos_operaciones_programadas.xlsx')

operaciones = operaciones_df['Código operación'].tolist()
quirofanos = costes_df['Unnamed: 0'].tolist()

# FUNCIONES
# Operaciones incompatibles
def son_incompatibles(operaciones):
    incompatibilidades = {}
    for i, op1 in operaciones.iterrows():
        incompatibilidades[op1['Código operación']] = [op2['Código operación']
            for h, op2 in operaciones.iterrows()
            if op2['Hora inicio '] < op1['Hora fin'] and op2['Hora fin'] > op1['Hora inicio ']
            and op2['Código operación'] != op1['Código operación']] # No es incompatible consigo misma
    return incompatibilidades

# Generar la planificación inicial
def generar_planificacion_inicial(operaciones, incompatibilidades):
    planificaciones = [] 
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
    asignar_planificaciones(operaciones, planificaciones)

    return planificaciones

# Modelo maestro con variables continuas
def modelo_maestro(planificacion, operaciones, incompatibilidades):
    modelo = LpProblem('Restringido', LpMinimize)
    # Variables
    x = LpVariable.dicts('x', [k for k in range(len(planificacion))], lowBound=0) 
    # Función Objetivo
    modelo += lpSum(x[k] for k in range(len(planificacion)))
    # Parámetros
    Bik={}
    for k in range(len(planificacion)):
        for i in operaciones:
            Bik[(i,k)] = 1 if i in planificacion[k] else 0
    # Restricciones
    for i in operaciones:
        modelo += lpSum(x[k]*Bik[(i,k)] for k in range(len(planificacion))) >=1
    # Resolver el modelo
    modelo.solve()
    # Imprimir resultados
    print("\nEstado del modelo:", LpStatus[modelo.status])
    print("Valor de la función objetivo:", value(modelo.objective))
    print("\nValores de las variables x distintas de 0 y su planificación:")
    for k in range(len(planificacion)):
        if value(x[k]) != 0:  
            print(f"x[{k}] = {value(x[k])}")
    # Calcular precios sombra
    precios_sombra = {}
    for op, restriccion in zip(operaciones, modelo.constraints.values()):
        precios_sombra[op] = restriccion.pi
    # Valor de la funcion objetivo
    valor_objetivo = value(modelo.objective)
    
    return modelo, valor_objetivo, precios_sombra

# Modelo maestro con variables enteras
def modelo_maestro_entero(planificacion, operaciones, incompatibilidades):
    modelo = LpProblem('Restringido', LpMinimize)
    
    x = LpVariable.dicts('x', [k for k in range(len(planificacion))], lowBound=0, cat=LpInteger) 
    
    modelo += lpSum(x[k] for k in range(len(planificacion)))
    
    Bik={}
    for k in range(len(planificacion)):
        for i in operaciones:
            Bik[(i,k)] = 1 if i in planificacion[k] else 0
    
    for i in operaciones:
        modelo += lpSum(x[k]*Bik[(i,k)] for k in range(len(planificacion))) >=1
    
    modelo.solve()
    
    print("\nEstado del modelo:", LpStatus[modelo.status])
    print("Valor de la función objetivo:", value(modelo.objective))
    print("\nValores de las variables x distintas de 0 y su planificación:")
    for k in range(len(planificacion)):
        if value(x[k]) != 0:
            print(f"x[{k}] = {value(x[k])}, Planificación: {planificacion[k]}")
            
    precios_sombra = {}
    for op, restriccion in zip(operaciones, modelo.constraints.values()):
        precios_sombra[op] = restriccion.pi
    
    valor_objetivo = value(modelo.objective)
    return modelo, valor_objetivo, precios_sombra

# Subproblema generación de columnas
def subproblema(operaciones, incompatibilidades, precios_sombra):
    # Modelo
    subproblema = LpProblem("Subproblema", LpMaximize)
    # Variables
    y = LpVariable.dicts('y', [i for i in operaciones], cat=LpBinary)
    # Función objetivo
    subproblema += lpSum(precios_sombra[i] * y[i] for i in operaciones)
    # Restricciones: la planificación generada no tenga operaciones incompatibles 
    for i in operaciones:
       for j in incompatibilidades.get(i, []):  
          subproblema += y[i] + y[j] <= 1 
    # Resolver el modelo
    subproblema.solve()
    # Imprimir resultados
    print("\nEstado del modelo:", LpStatus[subproblema.status])
    print("Valor de la función objetivo:", value(subproblema.objective))
    print("\nValores de las variables y (distintos de 0):")
    for i in operaciones:
        if y[i].varValue != 0:
            print(f"Operación {i}: y = {y[i].varValue}")
    # Generar la nueva planificación factible
    nueva_planificacion = [i for i in operaciones if y[i].varValue == 1]
    # Valor de la función objetivo
    valor_objetivo = value(subproblema.objective)

    return nueva_planificacion, valor_objetivo

# RESOLUCIÓN DEL PROBLEMA
incompatibilidades = son_incompatibles(operaciones_df)
planificacion_inicial = generar_planificacion_inicial(operaciones_df, incompatibilidades)

# Bucle generación de columnas
# Número máximo de iteraciones
num_iteraciones_max = 20
iteracion = 0

while iteracion < num_iteraciones_max:
    print(f"\nIteración {iteracion + 1} de {num_iteraciones_max}")
    
    # 1. Resolver el modelo restringido
    modelo, valor_objetivo_maestro, precios_sombra = modelo_maestro(planificacion_inicial, operaciones, incompatibilidades)
    
    # 2. Resolver el subproblema con los precios sombra obtenidos
    nueva_planificacion, valor_objetivo_subproblema =  subproblema(operaciones, incompatibilidades, precios_sombra)
    
    # 3. Verificar si la función objetivo del subproblema es > 1
    if valor_objetivo_subproblema > 1:
        print("La función objetivo del subproblema es mayor que 1, añadimos la nueva planificación.")
        planificacion_inicial.append(nueva_planificacion) 
    else:
        print("La función objetivo del subproblema no es mayor que 1, termina el proceso.")
        break 

    iteracion += 1

# Una vez terminado el bucle, resolvemos el modelo maestro entero con todas las planificaciones iniciales y las obtenidas con la generación de columnas
modelo_final, fo_final, precios_sombra_final = modelo_maestro_entero(planificacion_inicial, operaciones, incompatibilidades)

print('Número de quirófanos necesarios:', fo_final)







