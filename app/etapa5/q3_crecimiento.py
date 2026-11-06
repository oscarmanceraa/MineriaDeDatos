"""Consultas y resultados de la pregunta 3 de la Etapa 05: crecimiento temporal 2024-2026."""

from pathlib import Path

from app.etapa5.db import conexion, fetch

BASE = Path(__file__).resolve().parents[2]


def _consulta(conn, sql, parametros=()):
    return fetch(conn, sql, parametros)


def _opcion(valor, opciones, nombre):
    if valor in (None, ""):
        return None
    if valor not in opciones:
        raise ValueError(f"El filtro de {nombre} no corresponde a una opción disponible.")
    return valor


def _porcentaje(numerador, denominador):
    return round(numerador * 100 / denominador, 2) if denominador else 0.0


_NIVELES = {
    "anio": ("COALESCE(anio::text, 'Sin año')", "anio", "anio NULLS LAST"),
    "trimestre": (
        "COALESCE(anio::text, 'Sin año') || ' · ' || COALESCE(trimestre, 'Sin Trimestre')",
        "anio, trimestre",
        "anio NULLS LAST, trimestre",
    ),
    "mes": (
        "COALESCE(anio::text, 'Sin año') || ' · ' || COALESCE(mes_nombre, 'Sin Mes')",
        "anio, mes, mes_nombre",
        "anio NULLS LAST, mes NULLS LAST",
    ),
}


def _matriz(filas, nivel, pivot):
    periodos = list(dict.fromkeys(str(fila["periodo"]) for fila in filas))
    fuentes = list(dict.fromkeys(str(fila["fuente"]) for fila in filas))
    celdas = {}
    for fila in filas:
        periodo = str(fila["periodo"])
        fuente = str(fila["fuente"])
        celdas.setdefault(periodo, {})[fuente] = {
            "periodo": periodo,
            "fuente": fuente,
            "ocurrencias": int(fila["ocurrencias"]),
            "cantidad_registros": int(fila["cantidad_registros"]),
            "promedio_cantidad_por_ocurrencia": float(fila["promedio_cantidad_por_ocurrencia"] or 0),
            "especies_identificadas": int(fila["especies_identificadas"]),
            "porcentaje_ocurrencias": float(fila["porcentaje_ocurrencias"] or 0),
        }

    if pivot:
        filas_salida = fuentes
        columnas_salida = periodos
        celdas_salida = {}
        for fuente in fuentes:
            celdas_salida[fuente] = {}
            for periodo in periodos:
                celdas_salida[fuente][periodo] = celdas.get(periodo, {}).get(fuente)
    else:
        filas_salida = periodos
        columnas_salida = fuentes
        celdas_salida = {periodo: {fuente: celdas.get(periodo, {}).get(fuente) for fuente in fuentes} for periodo in periodos}

    return {
        "nivel": nivel,
        "pivot": pivot,
        "filas": filas_salida,
        "columnas": columnas_salida,
        "celdas": celdas_salida,
    }


def _conocimientos(conn, fuente, grupo, total, conteos_anio, conteos_fuente_2025, conteos_grupo, conteos_grupo_anio):
    y24 = conteos_anio.get(2024, 0)
    y25 = conteos_anio.get(2025, 0)
    y26 = conteos_anio.get(2026, 0)
    crecimiento = _porcentaje(y25 - y24, y24) if y24 else 0.0

    fuente_lider_2025 = max(conteos_fuente_2025.items(), key=lambda item: item[1], default=(None, 0))
    grupo_lider = max(conteos_grupo.items(), key=lambda item: item[1], default=(None, 0))
    grupo_lider_2025 = conteos_grupo_anio.get(grupo_lider[0], {}).get(2025, 0)

    seleccion = (
        f"fuente: {fuente or 'todas'}; grupo taxonómico: {grupo or 'todos'}; "
        "periodo fijo 2024-2026."
    )

    conocimientos = []
    if total:
        conocimientos.append(
            {
                "titulo": "El crecimiento 2024→2025 se concentra en una fuente",
                "pregunta": "¿Qué fuente explica el aumento de ocurrencias entre 2024 y 2025?",
                "dimensiones": "Tiempo (año), Fuente (dataset_origen) y Taxón (grupo taxonómico, como filtro). Medidas: ocurrencias y especies identificadas únicas.",
                "procedimiento": (
                    f"Filtros {seleccion} Se agruparon las ocurrencias por año y fuente sobre el periodo 2024-2026; "
                    "la variación 2024→2025 se calculó como (ocurrencias 2025 - ocurrencias 2024) / ocurrencias 2024. "
                    "No se promedian ni suman porcentajes entre fuentes."
                ),
                "evidencia": (
                    f"2024: {y24:,} ocurrencias; 2025: {y25:,}; variación {crecimiento:+.2f}%. "
                    f"Fuente líder en 2025: {fuente_lider_2025[0]} con {fuente_lider_2025[1]:,} ocurrencias."
                ),
                "hallazgo": (
                    f"Las ocurrencias pasaron de {y24:,} en 2024 a {y25:,} en 2025 ({crecimiento:+.2f}%); "
                    "el aumento no se distribuye de forma homogénea entre las fuentes."
                ),
                "interpretacion": (
                    "Frente al resumen temporal de etapa 4, el cruce por fuente muestra que el crecimiento reciente "
                    "depende de la incorporación masiva de una fuente. Es una asociación descriptiva entre periodo y "
                    "procedencia; no demuestra una causa ecológica ni un cambio real en la fauna."
                ),
                "utilidad": (
                    "Priorizar la revisión de la cobertura, fecha y método de la fuente que más crece antes de "
                    "interpretar el aumento como un cambio en la biodiversidad."
                ),
                "limitacion": (
                    "2026 está incompleto (corte 08/09/2026) y las ocurrencias no equivalen a individuos ni a esfuerzo "
                    "de muestreo. El crecimiento puede reflejar carga de datos, no un fenómeno biológico."
                ),
            }
        )

    if grupo_lider[0]:
        pct_grupo = _porcentaje(grupo_lider[1], total)
        pct_grupo_2025 = _porcentaje(grupo_lider_2025, y25) if y25 else 0.0
        conocimientos.append(
            {
                "titulo": "El crecimiento no es homogéneo por grupo taxonómico",
                "pregunta": "¿Qué grupo taxonómico concentra más ocurrencias en el periodo y en 2025?",
                "dimensiones": "Taxón (grupo taxonómico), Tiempo (año) y Fuente (dataset_origen, como filtro). Medidas: ocurrencias y especies identificadas únicas.",
                "procedimiento": (
                    f"Filtros {seleccion} Se agruparon las ocurrencias por grupo taxonómico y año; se calculó la "
                    "participación del grupo líder sobre el total del periodo y sobre 2025. Las especies únicas por "
                    "grupo no se suman entre grupos."
                ),
                "evidencia": (
                    f"{grupo_lider[0]}: {grupo_lider[1]:,} ocurrencias ({pct_grupo:.2f}% del periodo); "
                    f"en 2025 aporta {grupo_lider_2025:,} de {y25:,} ({pct_grupo_2025:.2f}%)."
                ),
                "hallazgo": (
                    f"El grupo líder concentra {pct_grupo:.2f}% de las ocurrencias del periodo y {pct_grupo_2025:.2f}% "
                    "de las de 2025; el crecimiento reciente no se reparte por igual entre grupos."
                ),
                "interpretacion": (
                    "Frente a los perfiles taxonómicos de etapa 4, el cruce tiempo × grupo muestra que el aumento se "
                    "concentra en ciertos grupos, posiblemente por la procedencia de las fuentes recientes. Es una "
                    "asociación descriptiva y no implica un cambio ecológico causal."
                ),
                "utilidad": (
                    "Orientar la verificación taxonómica y de cobertura hacia los grupos que más crecen, sin asumir "
                    "que el aumento corresponde a mayor abundancia."
                ),
                "limitacion": (
                    "Los grupos pueden solaparse con categorías de etapa 4 y las ocurrencias no miden individuos. "
                    "No se corrige por esfuerzo de observación ni por la carga diferencial de cada fuente."
                ),
            }
        )

    return conocimientos


def q3_datos(fuente=None, grupo=None, nivel="anio", pivot=False, operacion=None):
    if nivel not in _NIVELES:
        raise ValueError("El nivel temporal solicitado no está disponible.")

    with conexion() as conn:
        opciones_fuente = [
            fila["dataset_origen"]
            for fila in fetch(conn, "SELECT DISTINCT dataset_origen FROM dim_fuente ORDER BY dataset_origen")
        ]
        opciones_grupo = [
            fila["clase_grupo"]
            for fila in fetch(conn, "SELECT DISTINCT clase_grupo FROM dim_taxon ORDER BY clase_grupo")
        ]

        fuente = _opcion(fuente, opciones_fuente, "fuente")
        grupo = _opcion(grupo, opciones_grupo, "grupo taxonómico")

        select_expr, group_by, order_by = _NIVELES[nivel]
        params = (fuente, fuente, grupo, grupo)

        sql_matriz = f"""
            SELECT
                {select_expr} AS periodo,
                dataset_origen AS fuente,
                COUNT(*) AS ocurrencias,
                COALESCE(SUM(cantidad_registros), 0) AS cantidad_registros,
                AVG(cantidad_registros) AS promedio_cantidad_por_ocurrencia,
                COUNT(DISTINCT CASE WHEN especie <> 'Sin Identificar' THEN especie END) AS especies_identificadas,
                COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0) AS porcentaje_ocurrencias
            FROM v_registros_analitico
            WHERE anio BETWEEN 2024 AND 2026
              AND (%s::text IS NULL OR dataset_origen = %s)
              AND (%s::text IS NULL OR clase_grupo = %s)
            GROUP BY {group_by}, dataset_origen
            ORDER BY {order_by}, fuente
        """
        filas_matriz = fetch(conn, sql_matriz, params)

        sql_anios = """
            SELECT anio, COUNT(*) AS n
            FROM v_registros_analitico
            WHERE anio BETWEEN 2024 AND 2026
              AND (%s::text IS NULL OR dataset_origen = %s)
              AND (%s::text IS NULL OR clase_grupo = %s)
            GROUP BY anio
            ORDER BY anio
        """
        filas_anios = fetch(conn, sql_anios, params)
        conteos_anio = {int(fila["anio"]): int(fila["n"]) for fila in filas_anios if fila["anio"] is not None}

        sql_especies = """
            SELECT COUNT(DISTINCT CASE WHEN especie <> 'Sin Identificar' THEN especie END) AS n
            FROM v_registros_analitico
            WHERE anio BETWEEN 2024 AND 2026
              AND (%s::text IS NULL OR dataset_origen = %s)
              AND (%s::text IS NULL OR clase_grupo = %s)
        """
        especies = int(fetch(conn, sql_especies, params)[0]["n"])

        sql_fuentes_anio = """
            SELECT dataset_origen, anio, COUNT(*) AS n
            FROM v_registros_analitico
            WHERE anio = 2025
              AND (%s::text IS NULL OR dataset_origen = %s)
              AND (%s::text IS NULL OR clase_grupo = %s)
            GROUP BY dataset_origen, anio
            ORDER BY n DESC
        """
        filas_fuentes_2025 = fetch(conn, sql_fuentes_anio, params)
        conteos_fuente_2025 = {str(fila["dataset_origen"]): int(fila["n"]) for fila in filas_fuentes_2025}

        sql_grupos = """
            SELECT clase_grupo, COUNT(*) AS n
            FROM v_registros_analitico
            WHERE anio BETWEEN 2024 AND 2026
              AND (%s::text IS NULL OR dataset_origen = %s)
              AND (%s::text IS NULL OR clase_grupo = %s)
            GROUP BY clase_grupo
            ORDER BY n DESC
        """
        filas_grupos = fetch(conn, sql_grupos, params)
        conteos_grupo = {str(fila["clase_grupo"]): int(fila["n"]) for fila in filas_grupos}

        sql_grupos_anio = """
            SELECT clase_grupo, anio, COUNT(*) AS n
            FROM v_registros_analitico
            WHERE anio BETWEEN 2024 AND 2026
              AND (%s::text IS NULL OR dataset_origen = %s)
              AND (%s::text IS NULL OR clase_grupo = %s)
            GROUP BY clase_grupo, anio
        """
        filas_grupos_anio = fetch(conn, sql_grupos_anio, params)
        conteos_grupo_anio = {}
        for fila in filas_grupos_anio:
            conteos_grupo_anio.setdefault(str(fila["clase_grupo"]), {})[int(fila["anio"])] = int(fila["n"])

        sql_chart_anios = """
            SELECT anio, dataset_origen, COUNT(*) AS n
            FROM v_registros_analitico
            WHERE anio BETWEEN 2024 AND 2026
              AND (%s::text IS NULL OR dataset_origen = %s)
              AND (%s::text IS NULL OR clase_grupo = %s)
            GROUP BY anio, dataset_origen
            ORDER BY anio, dataset_origen
        """
        filas_chart_anios = fetch(conn, sql_chart_anios, params)

        sql_chart_grupos = """
            SELECT clase_grupo, COUNT(*) AS n
            FROM v_registros_analitico
            WHERE anio BETWEEN 2024 AND 2026
              AND (%s::text IS NULL OR dataset_origen = %s)
              AND (%s::text IS NULL OR clase_grupo = %s)
            GROUP BY clase_grupo
            ORDER BY n DESC
        """
        filas_chart_grupos = fetch(conn, sql_chart_grupos, params)

    matriz = _matriz(filas_matriz, nivel, pivot)

    total = sum(int(fila["ocurrencias"]) for fila in filas_matriz)
    y24 = conteos_anio.get(2024, 0)
    y25 = conteos_anio.get(2025, 0)
    crecimiento = _porcentaje(y25 - y24, y24) if y24 else 0.0

    # chart por año y fuente
    fuentes_chart = list(dict.fromkeys(str(fila["dataset_origen"]) for fila in filas_chart_anios))
    anios_chart = [2024, 2025, 2026]
    series_anios = []
    for fuente_chart in fuentes_chart:
        valores = []
        for anio in anios_chart:
            valor = next(
                (int(fila["n"]) for fila in filas_chart_anios if int(fila["anio"]) == anio and str(fila["dataset_origen"]) == fuente_chart),
                0,
            )
            valores.append(valor)
        series_anios.append({"nombre": fuente_chart, "valores": valores})

    grafico_anios = {"etiquetas": [str(a) for a in anios_chart], "series": series_anios}

    grafico_grupos = {
        "etiquetas": [str(fila["clase_grupo"]) for fila in filas_chart_grupos],
        "valores": [int(fila["n"]) for fila in filas_chart_grupos],
    }

    conocimientos = _conocimientos(
        conn,
        fuente,
        grupo,
        total,
        conteos_anio,
        conteos_fuente_2025,
        conteos_grupo,
        conteos_grupo_anio,
    )

    etiqueta_nivel = {"anio": "Año", "trimestre": "Trimestre", "mes": "Mes"}[nivel]

    return {
        "filtros": {
            "fuente": fuente,
            "grupo": grupo,
            "nivel": nivel,
            "pivot": pivot,
        },
        "etiquetas": {
            "fuente": fuente or "Todas las fuentes",
            "grupo": grupo or "Todos los grupos",
            "nivel": etiqueta_nivel,
            "periodo": "2024-2026",
        },
        "opciones": {
            "fuentes": opciones_fuente,
            "grupos": opciones_grupo,
            "niveles": ["anio", "trimestre", "mes"],
        },
        "indicadores": [
            {
                "etiqueta": "Ocurrencias del periodo",
                "valor": f"{total:,}",
                "detalle": "COUNT(*) de registros de ocurrencia entre 2024 y 2026 tras aplicar filtros.",
            },
            {
                "etiqueta": "Crecimiento 2024 → 2025",
                "valor": f"{crecimiento:+.2f}%",
                "detalle": f"{y24:,} ocurrencias en 2024 y {y25:,} en 2025; 2026 está incompleto.",
            },
            {
                "etiqueta": "Especies identificadas únicas",
                "valor": f"{especies:,}",
                "detalle": "COUNT DISTINCT de especie en 2024-2026, excluyendo 'Sin Identificar'.",
            },
        ],
        "matriz": matriz,
        "grafico_anios": grafico_anios,
        "grafico_grupos": grafico_grupos,
        "conocimientos": conocimientos,
        "interpretacion": (
            "La vista fija el periodo 2024-2026 y distingue ocurrencias por año, fuente y grupo taxonómico. "
            "El crecimiento 2024→2025 se recalcula con los filtros activos; el promedio de cantidad_registros se "
            "recalcula en cada celda y no se promedian entre grupos. 2026 es parcial y no debe compararse como año "
            "completo con 2024 o 2025."
        ),
        "limitacion": (
            "El modelo cuenta registros de ocurrencia, no individuos ni esfuerzo de muestreo. El aumento puede "
            "responder a la carga de datos de una fuente. Las categorías sin identificar o sin mes/trimestre se "
            "conservan como estados desconocidos, no como respuestas negativas. La asociación entre periodo, fuente "
            "y taxón no demuestra causalidad."
        ),
        "decision": (
            "Contrastar el crecimiento 2024-2025 con la procedencia y fecha de carga de las fuentes antes de "
            "interpretarlo como un cambio en la biodiversidad; priorizar la verificación de los grupos y fuentes que "
            "más crecen."
        ),
        "fuente": "v_registros_analitico del modelo estrella consultada en Supabase.",
        "cobertura": "Periodo 2024-2026 (2026 parcial, corte 08/09/2026).",
    }
