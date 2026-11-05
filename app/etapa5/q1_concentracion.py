"""Consultas y resultados de la pregunta 1 de la Etapa 05."""

from pathlib import Path

from app.etapa5.db import conexion, fetch

BASE = Path(__file__).resolve().parents[2]
SQL_DIR = BASE / "etapa5" / "sql"


def _consulta(conn, nombre, parametros=()):
    sql = (SQL_DIR / f"{nombre}.sql").read_text(encoding="utf-8")
    return fetch(conn, sql, parametros)


def _opcion(valor, opciones, nombre):
    if valor in (None, ""):
        return None
    if valor not in opciones:
        raise ValueError(f"El filtro de {nombre} no corresponde a una opción disponible.")
    return valor


def _parametros(provincia, grupo, anio):
    return (provincia, provincia, grupo, grupo, anio, anio)


def _porcentaje(numerador, denominador):
    return round(numerador * 100 / denominador, 2) if denominador else 0.0


def _matriz(filas, nivel, pivote):
    eje_fila = "clase_grupo" if pivote else (
        "municipio" if nivel == "municipio" else "provincia"
    )
    eje_columna = "provincia" if pivote else "clase_grupo"
    clave_fila = "eje_fila" if pivote else eje_fila
    clave_columna = "eje_columna" if pivote else eje_columna
    etiquetas_filas = list(dict.fromkeys(str(fila[clave_fila]) for fila in filas))
    etiquetas_columnas = list(dict.fromkeys(str(fila[clave_columna]) for fila in filas))
    celdas = {}

    for fila in filas:
        if pivote:
            territorio = fila["eje_columna"]
            taxon = fila["eje_fila"]
        else:
            territorio = fila["municipio"] if nivel == "municipio" else fila["provincia"]
            taxon = fila["clase_grupo"]
        nombre_fila = str(fila[clave_fila])
        nombre_columna = str(fila[clave_columna])
        celdas.setdefault(nombre_fila, {})[nombre_columna] = {
            **fila,
            "territorio": territorio,
            "grupo_taxonomico": taxon,
        }

    return {
        "eje_fila": eje_fila.replace("_", " ").capitalize(),
        "eje_columna": eje_columna.replace("_", " ").capitalize(),
        "filas": etiquetas_filas,
        "columnas": etiquetas_columnas,
        "celdas": celdas,
    }


def _conocimientos(indicadores, provincias, matriz, filtros, nivel):
    total = int(indicadores["ocurrencias"])
    primero = provincias[0] if provincias else None
    celda_lider = max(
        (
            celda
            for celdas in matriz["celdas"].values()
            for celda in celdas.values()
        ),
        key=lambda celda: int(celda["ocurrencias"]),
        default=None,
    )
    seleccion = (
        f"provincia: {filtros['provincia'] or 'todas'}; "
        f"grupo taxonómico: {filtros['grupo'] or 'todos'}; "
        f"año: {filtros['anio'] or 'todo el periodo'}; nivel territorial: {nivel}."
    )

    conocimientos = []
    if primero:
        cantidad = int(primero["ocurrencias"])
        porcentaje = _porcentaje(cantidad, total)
        if not any(filtros.values()):
            registros_sin_provincia = next(
                (
                    int(fila["ocurrencias"])
                    for fila in provincias
                    if fila["provincia"] == "Sin Clasificar"
                ),
                0,
            )
            total_con_provincia = total - registros_sin_provincia
            porcentaje_con_provincia = _porcentaje(cantidad, total_con_provincia)
            interpretacion = (
                "Frente al resumen territorial de etapa 4, esta vista incluye las ocurrencias sin "
                f"provincia ({registros_sin_provincia:,}) en el denominador. El líder conserva "
                f"{cantidad:,} ocurrencias, pero representa {porcentaje:.2f}% de las {total:,} "
                f"ocurrencias actuales, frente a {porcentaje_con_provincia:.2f}% de las "
                f"{total_con_provincia:,} con provincia."
            )
        else:
            interpretacion = (
                "Frente al resumen agregado de etapa 4, esta selección vuelve a calcular la "
                "participación de la provincia líder dentro de los filtros activos. El porcentaje "
                "no debe compararse con una selección o denominador diferentes."
            )
        conocimientos.append(
            {
                "titulo": "Concentración de ocurrencias por provincia",
                "pregunta": "¿Qué participación tiene la provincia con más ocurrencias dentro de la selección?",
                "dimensiones": "Territorio (provincia y, al descender, municipio), Tiempo (año) y Taxón (grupo taxonómico). Medidas: ocurrencias, suma y promedio de cantidad_registros y especies identificadas únicas.",
                "procedimiento": (
                    f"Filtros {seleccion} Se agruparon ocurrencias por provincia y se recalculó "
                    "el porcentaje como ocurrencias de la provincia / ocurrencias de toda la selección."
                ),
                "evidencia": (
                    f"{primero['provincia']}: {cantidad:,} ocurrencias de {total:,} "
                    f"({porcentaje:.2f}% del total filtrado)."
                ),
                "hallazgo": (
                    f"La provincia líder representa {porcentaje:.2f}% de las ocurrencias seleccionadas; "
                    "el porcentaje usa como denominador todas las ocurrencias tras aplicar los filtros."
                ),
                "interpretacion": interpretacion,
                "utilidad": (
                    "Orientar una revisión posterior hacia territorios con mayor volumen registrado, "
                    "sin interpretar el volumen como abundancia real de fauna."
                ),
                "limitacion": (
                    "El volumen puede depender del esfuerzo de observación y de la cobertura de las fuentes; "
                    "no representa por sí solo abundancia ni diversidad ecológica."
                ),
            }
        )

    if celda_lider:
        ocurrencias = int(celda_lider["ocurrencias"])
        porcentaje = _porcentaje(ocurrencias, total)
        conocimientos.append(
            {
                "titulo": "Cruce territorial y taxonómico de mayor volumen",
                "pregunta": "¿Qué combinación de territorio y grupo taxonómico aporta más ocurrencias?",
                "dimensiones": "Territorio (provincia/municipio), Taxón (grupo taxonómico) y Tiempo (año). Medidas: ocurrencias, especies identificadas únicas y cantidad_registros.",
                "procedimiento": (
                    f"Filtros {seleccion} Se cruzó el nivel territorial visible con grupo taxonómico; "
                    "se ordenaron las celdas por ocurrencias y se calculó la participación de la celda "
                    "sobre las ocurrencias de la selección."
                ),
                "evidencia": (
                    f"{celda_lider['territorio']} × {celda_lider['grupo_taxonomico']}: "
                    f"{ocurrencias:,} ocurrencias "
                    f"({porcentaje:.2f}% de {total:,})."
                ),
                "hallazgo": (
                    f"La celda de mayor volumen representa {porcentaje:.2f}% del total de ocurrencias "
                    "filtradas; su cuota se recalcula al cambiar filtros o nivel."
                ),
                "interpretacion": (
                    "Frente a los totales provinciales de etapa 4, el cruce territorio × grupo taxonómico "
                    "identifica dónde se combina el volumen. La celda mostrada se recalcula con los filtros "
                    "y el nivel activos; es una asociación descriptiva, no una explicación causal."
                ),
                "utilidad": (
                    "Ayuda a priorizar combinaciones territorio–grupo para auditar calidad, cobertura y "
                    "esfuerzo de registro."
                ),
                "limitacion": (
                    "Las especies únicas de distintas celdas pueden solaparse y no deben sumarse; "
                    "los registros desconocidos permanecen como categorías del modelo."
                ),
            }
        )

    return conocimientos


def q1_datos(provincia=None, grupo=None, anio=None, nivel="provincia", pivot=False, operacion=None):
    with conexion() as conn:
        opciones_provincia = [
            fila["provincia"]
            for fila in fetch(
                conn,
                "SELECT DISTINCT provincia FROM dim_territorio ORDER BY provincia",
            )
        ]
        opciones_grupo = [
            fila["clase_grupo"]
            for fila in fetch(
                conn,
                "SELECT DISTINCT clase_grupo FROM dim_taxon ORDER BY clase_grupo",
            )
        ]
        opciones_anio = [
            str(fila["anio"])
            for fila in fetch(
                conn,
                "SELECT DISTINCT anio FROM dim_tiempo WHERE anio IS NOT NULL ORDER BY anio",
            )
        ]

        provincia = _opcion(provincia, opciones_provincia, "provincia")
        grupo = _opcion(grupo, opciones_grupo, "grupo taxonómico")
        anio = _opcion(anio, opciones_anio, "año")
        if nivel not in {"provincia", "municipio"}:
            raise ValueError("El nivel territorial solicitado no está disponible.")
        if nivel == "municipio" and provincia is None:
            raise ValueError("Selecciona una provincia antes de descender al nivel municipio.")

        anio_numero = int(anio) if anio else None
        parametros = _parametros(provincia, grupo, anio_numero)
        indicador = _consulta(conn, "q1_indicadores", parametros)[0]
        grafico_provincias = _consulta(conn, "q1_grafico_territorio", parametros)
        grafico_temporal = _consulta(conn, "q1_grafico_temporal", parametros)

        if nivel == "municipio":
            nombre_matriz = "q1_drill_down"
            parametros_matriz = (
                provincia,
                grupo,
                grupo,
                anio_numero,
                anio_numero,
            )
        elif operacion == "rollup":
            nombre_matriz = "q1_roll_up"
            parametros_matriz = parametros
        elif pivot:
            nombre_matriz = "q1_pivot"
            parametros_matriz = parametros
        elif anio_numero is not None:
            nombre_matriz = "q1_slice"
            parametros_matriz = (
                anio_numero,
                provincia,
                provincia,
                grupo,
                grupo,
            )
        else:
            nombre_matriz = "q1_matriz"
            parametros_matriz = parametros

        filas_matriz = _consulta(conn, nombre_matriz, parametros_matriz)

    matriz = _matriz(filas_matriz, nivel, pivot and nivel == "provincia")
    ocurrencias = int(indicador["ocurrencias"])
    suma_cantidad = int(indicador["cantidad_registros"])
    especies = int(indicador["especies_identificadas"])

    return {
        "filtros": {
            "provincia": provincia,
            "grupo": grupo,
            "anio": anio,
            "nivel": nivel,
            "pivot": pivot and nivel == "provincia",
        },
        "etiquetas": {
            "provincia": provincia or "Todas las provincias",
            "grupo": grupo or "Todos los grupos",
            "anio": anio or "Todo el periodo",
            "nivel": "Municipio" if nivel == "municipio" else "Provincia",
        },
        "opciones": {
            "provincias": opciones_provincia,
            "grupos": opciones_grupo,
            "anios": opciones_anio,
        },
        "indicadores": [
            {
                "etiqueta": "Ocurrencias (filas del hecho)",
                "valor": f"{ocurrencias:,}",
                "detalle": "COUNT(*) de registros de ocurrencia en la selección.",
            },
            {
                "etiqueta": "Cantidad de registros",
                "valor": f"{suma_cantidad:,}",
                "detalle": "SUM(cantidad_registros); es una medida distinta del conteo de filas.",
            },
            {
                "etiqueta": "Especies identificadas únicas",
                "valor": f"{especies:,}",
                "detalle": "COUNT DISTINCT de especie, excluyendo el valor explícito 'Sin Identificar'.",
            },
        ],
        "matriz": matriz,
        "grafico_provincias": {
            "etiquetas": [fila["provincia"] for fila in grafico_provincias[:15]],
            "ocurrencias": [int(fila["ocurrencias"]) for fila in grafico_provincias[:15]],
            "porcentajes": [float(fila["porcentaje_ocurrencias"]) for fila in grafico_provincias[:15]],
        },
        "grafico_temporal": {
            "etiquetas": [fila["periodo"] for fila in grafico_temporal],
            "ocurrencias": [int(fila["ocurrencias"]) for fila in grafico_temporal],
            "promedios": [
                float(fila["promedio_cantidad_por_ocurrencia"] or 0)
                for fila in grafico_temporal
            ],
        },
        "conocimientos": _conocimientos(
            indicador,
            grafico_provincias,
            matriz,
            {"provincia": provincia, "grupo": grupo, "anio": anio},
            nivel,
        ),
        "interpretacion": (
            "La vista distingue ocurrencias (filas del hecho), suma de cantidad_registros y especies "
            "identificadas únicas. Las participaciones se recalculan respecto de la selección activa; "
            "los promedios se vuelven a calcular en cada agrupación y no se promedian entre grupos. "
            "Los registros sin año o con taxón desconocido se conservan cuando el filtro no los excluye."
        ),
        "limitacion": (
            "El modelo cuenta registros de ocurrencia, no individuos ni esfuerzo de muestreo. "
            "Los valores 'Sin Clasificar', 'Sin Identificar' y otros faltantes del ETL representan "
            "información desconocida, no respuestas negativas ni ausencia de fauna. La asociación "
            "entre territorio, periodo y taxón no demuestra causalidad."
        ),
        "decision": (
            "Usar las celdas con mayor participación como punto de partida para revisar la cobertura "
            "y calidad de registros por territorio y grupo, antes de priorizar nuevos muestreos; no "
            "interpretar directamente un mayor volumen como mayor abundancia biológica."
        ),
        "fuente": "v_registros_analitico del modelo estrella consultada en Supabase.",
        "consulta_matriz": nombre_matriz,
    }
