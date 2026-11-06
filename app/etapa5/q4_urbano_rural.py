"""Consultas de la pregunta 4 de la Etapa 05: urbano/rural y amenaza.

Fuente: vista v_registros_analitico del modelo estrella en Supabase.
"""

from app.etapa5.db import conexion, fetch

PERIODOS = [
    {"valor": "todo", "etiqueta": "Todo el periodo (2000–2026)"},
    {"valor": "2024-2026", "etiqueta": "2024–2026 (2026 parcial)"},
    {"valor": "2024-2025", "etiqueta": "2024–2025 (años completos)"},
    {"valor": "2026", "etiqueta": "2026 (corte 08/09/2026)"},
]

CATEGORIAS = ["Todas", "Rural", "Urbana", "No Determinada"]
CONSERVACIONES = ["Todas", "Amenazadas"]
COLUMNAS_TERRITORIO = ["Rural", "Urbana", "No Determinada"]


def _periodo_condicion(periodo):
    if periodo == "2024-2026":
        return "anio BETWEEN 2024 AND 2026"
    if periodo == "2024-2025":
        return "anio BETWEEN 2024 AND 2025"
    if periodo == "2026":
        return "anio = 2026"
    return None


def _periodo_etiqueta(periodo):
    for item in PERIODOS:
        if item["valor"] == periodo:
            return item["etiqueta"]
    return PERIODOS[0]["etiqueta"]


def _condiciones(provincia, periodo, categoria, conservacion):
    where = []
    params = []
    if provincia and provincia != "todas":
        where.append("provincia = %s")
        params.append(provincia)
    periodo_sql = _periodo_condicion(periodo)
    if periodo_sql:
        where.append(periodo_sql)
    if categoria and categoria != "Todas":
        where.append("categoria_territorial = %s")
        params.append(categoria)
    if conservacion == "Amenazadas":
        where.append("flag_amenazada = 1")
    return where, params


def _where(where):
    return ("WHERE " + " AND ".join(where)) if where else ""


def _matriz(conn, where, params, fila_col, pivot):
    sql = f"""
        SELECT
            {fila_col} AS fila,
            categoria_territorial AS columna,
            COUNT(*) AS registros,
            COALESCE(SUM(flag_amenazada), 0) AS amenazados,
            COUNT(DISTINCT CASE WHEN especie <> 'Sin Identificar' THEN especie END) AS especies
        FROM v_registros_analitico
        {_where(where)}
        GROUP BY 1, 2
    """
    filas_raw = fetch(conn, sql, params)

    datos = {}
    for r in filas_raw:
        datos.setdefault(r["fila"], {})[r["columna"]] = {
            "registros": int(r["registros"]),
            "amenazados": int(r["amenazados"]),
            "especies": int(r["especies"]),
        }

    filas = sorted(
        datos,
        key=lambda k: (
            -sum(v["amenazados"] for v in datos[k].values()),
            -sum(v["registros"] for v in datos[k].values()),
            k,
        ),
    )
    columnas = [c for c in COLUMNAS_TERRITORIO if any(c in datos[f] for f in filas)]

    celdas = {}
    totales_fila = {}
    totales_col = {c: {"registros": 0, "amenazados": 0} for c in columnas}
    total = {"registros": 0, "amenazados": 0}

    for fila in filas:
        celdas[fila] = {}
        acumulado = {"registros": 0, "amenazados": 0}
        for col in columnas:
            valor = datos.get(fila, {}).get(col)
            if valor is None:
                celdas[fila][col] = None
                continue
            tasa = round(valor["amenazados"] / valor["registros"] * 100, 2) if valor["registros"] else 0.0
            celdas[fila][col] = {
                **valor,
                "tasa": tasa,
            }
            acumulado["registros"] += valor["registros"]
            acumulado["amenazados"] += valor["amenazados"]
            totales_col[col]["registros"] += valor["registros"]
            totales_col[col]["amenazados"] += valor["amenazados"]
            total["registros"] += valor["registros"]
            total["amenazados"] += valor["amenazados"]
        totales_fila[fila] = {
            **acumulado,
            "tasa": round(acumulado["amenazados"] / acumulado["registros"] * 100, 2) if acumulado["registros"] else 0.0,
        }

    for col in columnas:
        totales_col[col]["tasa"] = (
            round(totales_col[col]["amenazados"] / totales_col[col]["registros"] * 100, 2)
            if totales_col[col]["registros"]
            else 0.0
        )
    total["tasa"] = round(total["amenazados"] / total["registros"] * 100, 2) if total["registros"] else 0.0

    display_filas = []
    display_columnas = []
    display_celdas = {}

    if not pivot:
        display_filas = list(filas)
        display_columnas = list(columnas) + ["Total"]
        for fila in filas:
            display_celdas[fila] = {col: celdas[fila].get(col) for col in columnas}
            display_celdas[fila]["Total"] = totales_fila[fila]
    else:
        display_filas = list(columnas) + ["Total"]
        display_columnas = list(filas) + ["Total"]
        for col in columnas:
            display_celdas[col] = {fila: celdas[fila].get(col) for fila in filas}
            display_celdas[col]["Total"] = totales_col[col]
        display_celdas["Total"] = {fila: totales_fila[fila] for fila in filas}
        display_celdas["Total"]["Total"] = total

    return {
        "modo": "municipio" if fila_col == "municipio" else "provincia",
        "pivot": pivot,
        "filas": display_filas,
        "columnas": display_columnas,
        "celdas": display_celdas,
        "filas_raw": list(filas),
        "columnas_raw": list(columnas),
        "celdas_raw": celdas,
        "totales_fila": totales_fila,
        "totales_col": totales_col,
        "total": total,
    }


def _chart_barras(matriz, metrica="tasa"):
    filas = matriz["filas_raw"]
    columnas = matriz["columnas_raw"]
    celdas = matriz["celdas_raw"]

    filas = filas[:10]
    etiquetas = [f for f in filas]
    series = []
    for col in columnas:
        valores = []
        for fila in filas:
            celda = celdas.get(fila, {}).get(col)
            valores.append(celda[metrica] if celda else 0.0)
        series.append({"nombre": col, "valores": valores})

    return {"etiquetas": etiquetas, "series": series, "tipo": metrica}


def _chart_burbuja(conn, provincia, periodo):
    where, params = [], []
    if provincia and provincia != "todas":
        where.append("provincia = %s")
        params.append(provincia)
    periodo_sql = _periodo_condicion(periodo)
    if periodo_sql:
        where.append(periodo_sql)

    sql = f"""
        SELECT
            provincia,
            COUNT(*) AS registros,
            COALESCE(SUM(flag_amenazada), 0) AS amenazados,
            COUNT(DISTINCT CASE WHEN especie <> 'Sin Identificar' THEN especie END) AS especies
        FROM v_registros_analitico
        {_where(where)}
        GROUP BY provincia
        ORDER BY registros DESC
    """
    filas = fetch(conn, sql, params)
    puntos = []
    max_registros = max([int(r["registros"]) for r in filas], default=1)
    max_especies = max([int(r["especies"]) for r in filas], default=1)
    for r in filas:
        registros = int(r["registros"])
        amenazados = int(r["amenazados"])
        especies = int(r["especies"])
        tasa = round(amenazados / registros * 100, 2) if registros else 0.0
        puntos.append(
            {
                "provincia": r["provincia"],
                "x": registros,
                "y": tasa,
                "amenazados": amenazados,
                "especies": especies,
                "r": 5 + 16 * (especies / max_especies if max_especies else 0),
            }
        )
    return {"puntos": puntos, "max_registros": max_registros}


def _baseline(conn):
    filas = fetch(
        conn,
        """
        SELECT
            provincia,
            categoria_territorial,
            COUNT(*) AS registros,
            COALESCE(SUM(flag_amenazada), 0) AS amenazados
        FROM v_registros_analitico
        GROUP BY 1, 2
        """,
    )
    por_provincia = {}
    por_categoria = {}
    for r in filas:
        por_provincia.setdefault(r["provincia"], {"registros": 0, "amenazados": 0})
        por_provincia[r["provincia"]]["registros"] += int(r["registros"])
        por_provincia[r["provincia"]]["amenazados"] += int(r["amenazados"])
        por_categoria.setdefault(r["categoria_territorial"], {"registros": 0, "amenazados": 0})
        por_categoria[r["categoria_territorial"]]["registros"] += int(r["registros"])
        por_categoria[r["categoria_territorial"]]["amenazados"] += int(r["amenazados"])

    for clave, valor in por_provincia.items():
        valor["tasa"] = round(valor["amenazados"] / valor["registros"] * 100, 2) if valor["registros"] else 0.0
    for clave, valor in por_categoria.items():
        valor["tasa"] = round(valor["amenazados"] / valor["registros"] * 100, 2) if valor["registros"] else 0.0

    fuentes = fetch(
        conn,
        """
        SELECT dataset_origen, COUNT(*) AS registros, COALESCE(SUM(flag_amenazada), 0) AS amenazados
        FROM v_registros_analitico
        GROUP BY 1
        """,
    )
    ursidae = fetch(
        conn,
        """
        SELECT COUNT(*) AS registros
        FROM v_registros_analitico
        WHERE flag_amenazada = 1 AND familia = 'Ursidae'
        """,
    )[0]["registros"]

    total = fetch(
        conn,
        "SELECT COUNT(*) AS registros, COALESCE(SUM(flag_amenazada), 0) AS amenazados FROM v_registros_analitico",
    )[0]

    return {
        "total": {"registros": int(total["registros"]), "amenazados": int(total["amenazados"])},
        "provincias": por_provincia,
        "categorias": por_categoria,
        "fuentes": {r["dataset_origen"]: {"registros": int(r["registros"]), "amenazados": int(r["amenazados"])} for r in fuentes},
        "ursidae": int(ursidae),
    }


def _conocimientos(base):
    total_amen = base["total"]["amenazados"]
    rural = base["categorias"].get("Rural", {"registros": 0, "amenazados": 0, "tasa": 0})
    ud = base["categorias"].get("No Determinada", {"registros": 0, "amenazados": 0, "tasa": 0})
    urbana = base["categorias"].get("Urbana", {"registros": 0, "amenazados": 0, "tasa": 0})
    provincias = base["provincias"]
    guavio = provincias.get("Guavio", {"registros": 0, "amenazados": 0, "tasa": 0})
    distrito = provincias.get("Distrito Capital / Sabana", {"registros": 0, "amenazados": 0, "tasa": 0})
    tequendama = provincias.get("Tequendama", {"registros": 0, "amenazados": 0, "tasa": 0})
    gualiva = provincias.get("Gualivá", {"registros": 0, "amenazados": 0, "tasa": 0})
    ubate = provincias.get("Ubaté", {"registros": 0, "amenazados": 0, "tasa": 0})
    sibio = base["fuentes"].get("SIBIO CAR Cundinamarca", {"registros": 0, "amenazados": 0})

    pct_rural = round(rural["amenazados"] / total_amen * 100, 2) if total_amen else 0.0
    pct_ud = round(ud["amenazados"] / total_amen * 100, 2) if total_amen else 0.0
    pct_urbana = round(urbana["amenazados"] / total_amen * 100, 2) if total_amen else 0.0
    pct_sibio = round(sibio["amenazados"] / total_amen * 100, 2) if total_amen else 0.0

    k1 = {
        "titulo": "La amenaza se concentra en pocas provincias rurales, no en todas",
        "pregunta": "¿La categoría rural explica por sí sola una mayor tasa de amenaza en todas las provincias?",
        "dimensiones": "Territorio (provincia, categoría territorial) y Conservación (UICN).",
        "procedimiento": "Se agruparon los 20.087 registros por provincia y categoría territorial, se sumó la bandera CR/EN/VU y se calculó la tasa sobre los registros de cada celda.",
        "evidencia": (
            f"Guavio: {guavio['amenazados']} de {guavio['registros']:,} registros ({guavio['tasa']}%). "
            f"Ubaté: {ubate['amenazados']} de {ubate['registros']:,} ({ubate['tasa']}%). "
            f"Distrito Capital / Sabana: {distrito['amenazados']} de {distrito['registros']:,} ({distrito['tasa']}%). "
            f"Tequendama: {tequendama['amenazados']} de {tequendama['registros']:,} ({tequendama['tasa']}%) y "
            f"Gualivá: {gualiva['amenazados']} de {gualiva['registros']:,} ({gualiva['tasa']}%)."
        ),
        "hallazgo": (
            f"La tasa de Guavio ({guavio['tasa']}%) es decenas de veces mayor que la de Tequendama "
            f"({tequendama['tasa']}%) y Gualivá ({gualiva['tasa']}%), aunque las tres son mayoritariamente rurales. "
            "El comportamiento no es homogéneo dentro de lo rural."
        ),
        "interpretacion": (
            "La categoría rural no basta para explicar la amenaza. La concentración observada en Guavio, Ubaté y "
            "Almeidas coincide con registros de mamíferos y con monitoreo institucional, por lo que el patrón puede "
            "reflejar tanto una amenaza real como un esfuerzo de observación diferenciado."
        ),
        "utilidad": "Permite priorizar la verificación en provincias concretas en lugar de tratar todo lo rural como un solo bloque.",
        "limitacion": "Las tasas usan denominadores muy distintos y no corrigen por esfuerzo de muestreo ni por superficie; no prueban causalidad.",
    }

    k2 = {
        "titulo": "El sesgo de fuente y el vacío territorial explican parte de la concentración",
        "pregunta": "¿Cuánto de la concentración de registros amenazados depende de la fuente y de los registros sin territorio?",
        "dimensiones": "Conservación (UICN), Fuente (origen), Territorio (categoría territorial) y Taxón (familia).",
        "procedimiento": (
            "Se contaron los registros con bandera CR/EN/VU y se distribuyeron por categoría territorial, fuente y familia. "
            "Se calculó el peso de cada grupo sobre el total de amenazados y se identificó el aporte de SIBIO CAR y de Ursidae."
        ),
        "evidencia": (
            f"De {total_amen} registros amenazados, {rural['amenazados']} son rurales ({pct_rural}%), "
            f"{ud['amenazados']} no tienen territorio asignado ({pct_ud}%) y {urbana['amenazados']} son urbanos ({pct_urbana}%). "
            f"SIBIO CAR aporta {sibio['amenazados']} amenazados ({pct_sibio}% del total) y la familia Ursidae concentra "
            f"{base['ursidae']} de ellos."
        ),
        "hallazgo": (
            f"El 65,5% de los registros amenazados es rural, pero el 27,0% no tiene territorio. SIBIO CAR, con solo "
            f"{sibio['registros']} registros en total, aporta {sibio['amenazados']} amenazados y Ursidae concentra {base['ursidae']}."
        ),
        "interpretacion": (
            "La fuente institucional y un taxón específico explican buena parte de la concentración. Esto refuerza la "
            "hipótesis de sesgo de observación: donde hay monitoreo institucional aparecen más registros amenazados, "
            "sin que eso implique necesariamente mayor presión sobre el hábitat."
        ),
        "utilidad": "Sugiere contrastar los resultados con fuentes independientes y completar la georreferenciación antes de priorizar territorios.",
        "limitacion": "No se puede separar el efecto de la fuente del efecto ecológico real con los datos disponibles; la ausencia de registros no equivale a ausencia de amenaza.",
    }

    return [k1, k2]


def q4_datos(provincia="todas", periodo="todo", categoria="Todas", conservacion="Todas", pivot=False, drill=False):
    provincia = provincia or "todas"
    periodo = periodo or "todo"
    categoria = categoria or "Todas"
    conservacion = conservacion or "Todas"

    with conexion() as conn:
        provincias = [
            r["provincia"]
            for r in fetch(conn, "SELECT DISTINCT provincia FROM dim_territorio ORDER BY provincia")
        ]

        where, params = _condiciones(provincia, periodo, categoria, conservacion)
        fila_col = "municipio" if (drill and provincia != "todas") else "provincia"
        matriz = _matriz(conn, where, params, fila_col, pivot)
        metrica_barras = "registros" if conservacion == "Amenazadas" else "tasa"
        barras = _chart_barras(matriz, metrica_barras)
        burbuja = _chart_burbuja(conn, provincia, periodo)

        total = fetch(
            conn,
            f"""
            SELECT COUNT(*) AS registros, COALESCE(SUM(flag_amenazada), 0) AS amenazados
            FROM v_registros_analitico {_where(where)}
            """,
            params,
        )[0]
        categorias = fetch(
            conn,
            f"""
            SELECT categoria_territorial, COUNT(*) AS registros, COALESCE(SUM(flag_amenazada), 0) AS amenazados
            FROM v_registros_analitico {_where(where)}
            GROUP BY 1
            """,
            params,
        )

        base = _baseline(conn)

    registros = int(total["registros"])
    amenazados = int(total["amenazados"])
    tasa = round(amenazados / registros * 100, 2) if registros else 0.0

    rural = next((c for c in categorias if c["categoria_territorial"] == "Rural"), {"registros": 0, "amenazados": 0})
    rural_amen = int(rural["amenazados"])
    pct_rural_sel = round(rural_amen / amenazados * 100, 2) if amenazados else 0.0

    total_amen_global = base["total"]["amenazados"]
    pct_global = (
        round(amenazados / total_amen_global * 100, 2) if total_amen_global else 0.0
    )

    if conservacion == "Amenazadas":
        indicadores = [
            {
                "etiqueta": "Registros amenazados",
                "valor": f"{amenazados:,}",
                "detalle": "Registros CR/EN/VU dentro de la selección de provincia, periodo y categoría.",
            },
            {
                "etiqueta": "Peso sobre amenazados totales",
                "valor": f"{pct_global:.2f}%",
                "detalle": f"{amenazados:,} de {total_amen_global:,} registros amenazados del dataset completo.",
            },
            {
                "etiqueta": "Peso rural",
                "valor": f"{pct_rural_sel:.2f}%",
                "detalle": f"{rural_amen:,} de {amenazados:,} amenazados están en categoría rural.",
            },
        ]
    else:
        indicadores = [
            {
                "etiqueta": "Tasa de amenaza",
                "valor": f"{tasa:.2f}%",
                "detalle": f"{amenazados:,} registros CR/EN/VU sobre {registros:,} registros de la selección.",
            },
            {
                "etiqueta": "Registros amenazados",
                "valor": f"{amenazados:,}",
                "detalle": "Registros con categoría UICN CR, EN o VU dentro de la selección.",
            },
            {
                "etiqueta": "Peso rural",
                "valor": f"{pct_rural_sel:.2f}%",
                "detalle": f"{rural_amen:,} de {amenazados:,} amenazados están en categoría rural.",
            },
        ]

    nota_slice = (
        "Slice activo: solo se muestran registros CR/EN/VU; la tasa es 100% por construcción. "
        "Quita el slice para comparar contra el total."
        if conservacion == "Amenazadas"
        else ""
    )

    return {
        "ok": True,
        "error": None,
        "filtros": {
            "provincia": provincia,
            "periodo": periodo,
            "categoria": categoria,
            "conservacion": conservacion,
            "pivot": pivot,
            "drill": drill,
        },
        "opciones": {
            "provincias": provincias,
            "periodos": PERIODOS,
            "categorias": CATEGORIAS,
            "conservaciones": CONSERVACIONES,
        },
        "etiquetas": {
            "provincia": "Todas las provincias" if provincia == "todas" else provincia,
            "periodo": _periodo_etiqueta(periodo),
            "categoria": "Todas las categorías" if categoria == "Todas" else categoria,
            "conservacion": "Todos los estados" if conservacion == "Todas" else "Solo amenazadas (CR/EN/VU)",
        },
        "nota_slice": nota_slice,
        "periodo_texto": _periodo_etiqueta(periodo),
        "indicadores": indicadores,
        "matriz": matriz,
        "chart_barras": barras,
        "chart_burbuja": burbuja,
        "conocimientos": _conocimientos(base),
        "interpretacion": (
            "La tasa de amenaza no es un atributo estable de lo rural: depende de la provincia concreta y del esfuerzo "
            "de observación. Guavio, Ubaté y Almeidas concentran la mayor tasa, mientras provincias rurales con más "
            "registros, como Tequendama y Gualivá, presentan tasas cercanas a cero. La coincidencia con SIBIO CAR y "
            "Ursidae sugiere que parte del patrón es de monitoreo más que de amenaza real, hipótesis que debe "
            "contrastarse con otras fuentes."
        ),
        "limitacion": (
            "Los denominadores son muy distintos entre provincias, 47 amenazados no tienen territorio asignado y "
            "2026 está incompleto (corte 08/09/2026). Los registros no equivalen a individuos y no se corrige por "
            "esfuerzo de muestreo ni superficie; por tanto no se puede afirmar causalidad entre hábitat y amenaza."
        ),
        "decision": (
            "Priorizar la verificación en Guavio, Ubaté y Almeidas, completar la asignación territorial de los 47 "
            "registros amenazados sin provincia y contrastar los hallazgos con fuentes independientes antes de "
            "declarar prioridades de conservación."
        ),
        "fuente": "Dataset/Dataset.csv procesado en Supabase (modelo estrella, Etapa 05).",
        "cobertura": "20.087 registros de ocurrencia, periodo 2000–2026, corte 08/09/2026.",
    }
