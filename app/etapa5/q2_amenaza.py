"""Consultas y resultados de la pregunta 2 de la Etapa 05."""

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


def _parametros(fuente, grupo, amenazadas):
    marca_amenazadas = 1 if amenazadas else None
    return (
        fuente,
        fuente,
        grupo,
        grupo,
        marca_amenazadas,
        marca_amenazadas,
    )


def _porcentaje(numerador, denominador):
    return round(numerador * 100 / denominador, 2) if denominador else 0.0


def _matriz(filas, operacion):
    if operacion == "dice":
        clave_fila = "iucn_codigo"
        clave_columna = "dataset_origen"
        eje_fila = "Código / estado UICN"
        eje_columna = "Fuente"
    else:
        clave_fila = "clase_grupo"
        clave_columna = "dataset_origen"
        eje_fila = "Grupo taxonómico"
        eje_columna = "Fuente"

    def nombre_fila(fila):
        if operacion == "dice":
            return f"{fila['iucn_codigo']} · {fila['iucn_estado']}"
        return str(fila[clave_fila])

    etiquetas_filas = list(dict.fromkeys(nombre_fila(fila) for fila in filas))
    etiquetas_columnas = list(dict.fromkeys(str(fila[clave_columna]) for fila in filas))
    celdas = {}
    for fila in filas:
        nombre = nombre_fila(fila)
        nombre_columna = str(fila[clave_columna])
        celdas.setdefault(nombre, {})[nombre_columna] = fila

    return {
        "eje_fila": eje_fila,
        "eje_columna": eje_columna,
        "filas": etiquetas_filas,
        "columnas": etiquetas_columnas,
        "celdas": celdas,
        "slice": operacion == "slice",
    }


def _conocimientos(indicadores, fuentes, matriz_evidencia, filtros):
    total_amenazadas = int(indicadores["ocurrencias_amenazadas"])
    ocurrencias = int(indicadores["ocurrencias"])
    seleccion = (
        f"fuente: {filtros['fuente'] or 'todas'}; "
        f"grupo taxonómico: {filtros['grupo'] or 'todos'}; "
        f"slice CR/EN/VU: {'activo' if filtros['amenazadas'] else 'inactivo'}."
    )

    conocimientos = []
    if fuentes:
        fuente_lider = fuentes[0]
        cantidad = int(fuente_lider["ocurrencias_amenazadas"])
        porcentaje = _porcentaje(cantidad, total_amenazadas)
        conocimientos.append(
            {
                "titulo": "Participación de las fuentes en las ocurrencias amenazadas",
                "pregunta": "¿Qué fuente aporta más ocurrencias con estado CR, EN o VU dentro de la selección?",
                "dimensiones": "Fuente (dataset_origen) y Conservación (código/estado UICN). Medidas: ocurrencias, ocurrencias amenazadas, promedio de cantidad_registros y especies amenazadas identificadas únicas.",
                "procedimiento": (
                    f"Filtros {seleccion} Se agruparon los hechos por fuente y se recalculó la "
                    "participación de ocurrencias amenazadas sobre el total amenazado de la selección."
                ),
                "evidencia": (
                    f"{fuente_lider['dataset_origen']}: {cantidad:,} ocurrencias amenazadas "
                    f"({porcentaje:.2f}% de {total_amenazadas:,})."
                    if total_amenazadas
                    else f"No hay ocurrencias CR/EN/VU en la selección de {ocurrencias:,} ocurrencias."
                ),
                "hallazgo": (
                    f"La fuente líder reúne {cantidad:,} ocurrencias amenazadas "
                    f"({porcentaje:.2f}% del total amenazado de la selección)."
                    if total_amenazadas
                    else "La selección no contiene ocurrencias clasificadas CR/EN/VU."
                ),
                "interpretacion": (
                    "Frente a los resúmenes de etapa 4, esta vista calcula la participación de cada fuente "
                    "sobre las ocurrencias amenazadas del corte consultado. El JSON territorial de etapa 4 "
                    "también reporta 174, mientras el JSON multivariado reporta 330; la diferencia entre "
                    "estos dos artefactos queda POR CONFIRMAR y no se interpreta como cambio temporal."
                ),
                "utilidad": (
                    "Priorizar la revisión de consistencia, cobertura temporal y geográfica en las fuentes "
                    "que más contribuyen a los registros amenazados."
                ),
                "limitacion": (
                    "Más registros en una fuente no demuestran mayor amenaza ecológica; las fuentes pueden "
                    "diferir en esfuerzo y método de observación."
                ),
            }
        )

    celdas = [
        celda
        for valores in matriz_evidencia["celdas"].values()
        for celda in valores.values()
    ]
    celda_lider = max(
        celdas,
        key=lambda celda: int(celda["ocurrencias_amenazadas"]),
        default=None,
    )
    if celda_lider:
        cantidad = int(celda_lider["ocurrencias_amenazadas"])
        porcentaje = _porcentaje(cantidad, total_amenazadas)
        conocimientos.append(
            {
                "titulo": "Cruce de grupo taxonómico y fuente",
                "pregunta": "¿Qué combinación de grupo taxonómico y fuente concentra más ocurrencias amenazadas?",
                "dimensiones": "Taxón (grupo taxonómico), Fuente (dataset_origen) y Conservación (flag CR/EN/VU y estado UICN). Medidas: ocurrencias, suma/promedio de cantidad_registros y especies amenazadas identificadas únicas.",
                "procedimiento": (
                    f"Filtros {seleccion} Se cruzaron grupo taxonómico y fuente. La cuota de cada celda "
                    "se recalculó sobre la suma de ocurrencias amenazadas de la selección."
                ),
                "evidencia": (
                    f"{celda_lider['clase_grupo']} × {celda_lider['dataset_origen']}: "
                    f"{cantidad:,} ocurrencias amenazadas "
                    f"({porcentaje:.2f}% de {total_amenazadas:,})."
                    if total_amenazadas
                    else f"La selección contiene {ocurrencias:,} ocurrencias y ninguna clasificada CR/EN/VU."
                ),
                "hallazgo": (
                    f"La celda principal representa {porcentaje:.2f}% de las ocurrencias amenazadas "
                    "de la selección."
                    if total_amenazadas
                    else "No se observa una celda con ocurrencias CR/EN/VU en esta selección."
                ),
                "interpretacion": (
                    "Frente a los perfiles separados de etapa 4, el cruce taxón × fuente identifica la "
                    "combinación que concentra ocurrencias amenazadas. Debe leerse junto con la discrepancia "
                    "POR CONFIRMAR entre los 174 registros del JSON territorial y los 330 del JSON "
                    "multivariado; no demuestra causalidad."
                ),
                "utilidad": (
                    "Guiar auditorías de taxonomía y procedencia antes de usar los conteos para decidir "
                    "acciones de conservación."
                ),
                "limitacion": (
                    "Las especies distintas pueden aparecer en varias fuentes y no deben sumarse entre celdas; "
                    "los estados desconocidos o no evaluados no equivalen a una categoría negativa."
                ),
            }
        )

    return conocimientos


def q2_datos(fuente=None, grupo=None, amenazadas=False, operacion=None):
    if operacion not in (None, "", "slice", "dice"):
        raise ValueError("La operación OLAP solicitada no está disponible.")
    if operacion == "slice":
        amenazadas = True

    with conexion() as conn:
        opciones_fuente = [
            fila["dataset_origen"]
            for fila in fetch(
                conn,
                "SELECT DISTINCT dataset_origen FROM dim_fuente ORDER BY dataset_origen",
            )
        ]
        opciones_grupo = [
            fila["clase_grupo"]
            for fila in fetch(
                conn,
                "SELECT DISTINCT clase_grupo FROM dim_taxon ORDER BY clase_grupo",
            )
        ]

        fuente = _opcion(fuente, opciones_fuente, "fuente")
        grupo = _opcion(grupo, opciones_grupo, "grupo taxonómico")
        if operacion == "dice" and (fuente is None or grupo is None):
            raise ValueError("Para aplicar dice, selecciona una fuente y un grupo taxonómico.")

        parametros = _parametros(fuente, grupo, amenazadas)
        indicador = _consulta(conn, "q2_indicadores", parametros)[0]
        grafico_fuentes = _consulta(conn, "q2_grafico_fuentes", parametros)
        grafico_taxones = _consulta(conn, "q2_grafico_taxones", parametros)
        filas_evidencia = _consulta(conn, "q2_matriz", parametros)

        if operacion == "dice":
            filas_matriz = _consulta(
                conn,
                "q2_dice",
                (
                    fuente,
                    grupo,
                    1 if amenazadas else None,
                    1 if amenazadas else None,
                ),
            )
        elif amenazadas:
            filas_matriz = _consulta(
                conn,
                "q2_slice",
                (fuente, fuente, grupo, grupo),
            )
        else:
            filas_matriz = filas_evidencia

    matriz_evidencia = _matriz(filas_evidencia, None)
    matriz = _matriz(filas_matriz, operacion if operacion == "dice" else (
        "slice" if amenazadas else None
    ))
    ocurrencias = int(indicador["ocurrencias"])
    ocurrencias_amenazadas = int(indicador["ocurrencias_amenazadas"])
    especies_amenazadas = int(indicador["especies_amenazadas_identificadas"])
    porcentaje_amenazadas = float(indicador["porcentaje_amenazadas"] or 0)
    total_amenazado = sum(
        int(fila["ocurrencias_amenazadas"])
        for fila in grafico_fuentes
    )

    return {
        "filtros": {
            "fuente": fuente,
            "grupo": grupo,
            "amenazadas": amenazadas,
            "operacion": operacion or ("slice" if amenazadas else None),
        },
        "etiquetas": {
            "fuente": fuente or "Todas las fuentes",
            "grupo": grupo or "Todos los grupos",
            "conservacion": "Solo CR/EN/VU" if amenazadas else "Todos los estados",
            "operacion": "Dice por estado UICN" if operacion == "dice" else (
                "Slice CR/EN/VU" if amenazadas else "Cubo completo"
            ),
        },
        "opciones": {
            "fuentes": opciones_fuente,
            "grupos": opciones_grupo,
        },
        "indicadores": [
            {
                "etiqueta": "Ocurrencias de la selección",
                "valor": f"{ocurrencias:,}",
                "detalle": (
                    "COUNT(*) del modelo; con slice activo incluye solo CR/EN/VU."
                ),
            },
            {
                "etiqueta": "Ocurrencias amenazadas CR/EN/VU",
                "valor": f"{ocurrencias_amenazadas:,}",
                "detalle": (
                    f"{porcentaje_amenazadas:.2f}% de {ocurrencias:,} ocurrencias seleccionadas; "
                    "el denominador cambia con los filtros."
                ),
            },
            {
                "etiqueta": "Especies amenazadas identificadas",
                "valor": f"{especies_amenazadas:,}",
                "detalle": "COUNT DISTINCT en ocurrencias CR/EN/VU; excluye 'Sin Identificar'.",
            },
        ],
        "matriz": matriz,
        "grafico_fuentes": {
            "etiquetas": [fila["dataset_origen"] for fila in grafico_fuentes],
            "ocurrencias": [int(fila["ocurrencias"]) for fila in grafico_fuentes],
            "amenazadas": [int(fila["ocurrencias_amenazadas"]) for fila in grafico_fuentes],
            "tasas": [float(fila["porcentaje_amenazadas"] or 0) for fila in grafico_fuentes],
            "participaciones": [
                float(fila["porcentaje_del_total_amenazado"] or 0)
                for fila in grafico_fuentes
            ],
        },
        "grafico_taxones": {
            "etiquetas": [fila["clase_grupo"] for fila in grafico_taxones],
            "ocurrencias": [int(fila["ocurrencias"]) for fila in grafico_taxones],
            "amenazadas": [int(fila["ocurrencias_amenazadas"]) for fila in grafico_taxones],
            "tasas": [float(fila["porcentaje_amenazadas"] or 0) for fila in grafico_taxones],
            "participaciones": [
                float(fila["porcentaje_del_total_amenazado"] or 0)
                for fila in grafico_taxones
            ],
        },
        "conocimientos": _conocimientos(
            indicador,
            grafico_fuentes,
            matriz_evidencia,
            {"fuente": fuente, "grupo": grupo, "amenazadas": amenazadas},
        ),
        "interpretacion": (
            "Las ocurrencias amenazadas son registros con código CR, EN o VU; la tasa divide ese conteo "
            "entre todas las ocurrencias de la selección y se recalcula al aplicar filtros. El estado "
            "no evaluado (NE), los datos insuficientes y los faltantes no se interpretan como respuestas "
            "negativas. Las especies únicas por grupo o fuente pueden solaparse. El JSON territorial de "
            "etapa 4 reporta 174 ocurrencias amenazadas, igual que esta consulta; el JSON multivariado "
            "reporta 330, diferencia de corte o definición POR CONFIRMAR."
        ),
        "limitacion": (
            "El modelo cuenta ocurrencias, no individuos ni esfuerzo de muestreo. Las diferencias entre "
            "fuentes pueden reflejar sus métodos y cobertura; la concentración observada no prueba que una "
            "fuente, grupo o territorio cause mayor amenaza."
        ),
        "decision": (
            "Priorizar la revisión de procedencia, categoría UICN y consistencia taxonómica en los cruces "
            "con mayor volumen CR/EN/VU antes de convertirlos en prioridades de gestión."
        ),
        "fuente": "v_registros_analitico del modelo estrella consultada en Supabase.",
        "total_amenazado": total_amenazado,
    }
