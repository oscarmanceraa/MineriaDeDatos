"""Carga y consulta en SQLite del modelo estrella de la Etapa 05."""

from functools import lru_cache
from pathlib import Path
import sqlite3
import threading

import pandas as pd


BASE = Path(__file__).resolve().parent.parent
DATASET = BASE / "Dataset" / "Dataset.csv"
_LOCK = threading.RLock()


class ConsultaInvalida(ValueError):
    """Parámetros de exploración incompatibles con la vista."""


_JOINS = """
    FROM hecho_registros_ocurrencia h
    JOIN dim_tiempo t ON t.tiempo_key = h.tiempo_key
    JOIN dim_territorio r ON r.territorio_key = h.territorio_key
    JOIN dim_taxon x ON x.taxon_key = h.taxon_key
    JOIN dim_fuente u ON u.fuente_key = h.fuente_key
    JOIN dim_conservacion c ON c.conservacion_key = h.conservacion_key
"""

_AXES = {
    "provincia": {
        "label": "Provincia",
        "expression": "r.provincia",
        "order": "r.provincia",
    },
    "municipio": {
        "label": "Municipio",
        "expression": "r.provincia || ' · ' || r.municipio",
        "order": "r.provincia, r.municipio",
    },
    "categoria": {
        "label": "Categoría territorial",
        "expression": "r.categoria_territorial",
        "order": "r.categoria_territorial",
    },
    "grupo": {
        "label": "Grupo taxonómico",
        "expression": "x.clase_grupo",
        "order": "x.clase_grupo",
    },
    "clase": {
        "label": "Clase",
        "expression": "x.clase",
        "order": "x.clase",
    },
    "familia": {
        "label": "Familia",
        "expression": "x.familia",
        "order": "x.familia",
    },
    "especie": {
        "label": "Especie",
        "expression": "x.especie",
        "order": "x.especie",
    },
    "fuente": {
        "label": "Dataset de origen",
        "expression": "u.dataset_origen",
        "order": "u.dataset_origen",
    },
    "estado_iucn": {
        "label": "Estado IUCN",
        "expression": "c.iucn_estado",
        "order": "c.iucn_estado",
    },
    "codigo_iucn": {
        "label": "Código IUCN",
        "expression": "c.iucn_codigo",
        "order": "c.iucn_codigo",
    },
    "anio": {
        "label": "Año",
        "expression": "coalesce(CAST(t.anio AS TEXT), 'Sin año')",
        "order": "t.anio IS NULL, t.anio",
    },
    "trimestre": {
        "label": "Año y trimestre",
        "expression": (
            "CASE WHEN t.anio IS NULL THEN 'Sin año' "
            "ELSE CAST(t.anio AS TEXT) || ' · ' || t.trimestre END"
        ),
        "order": "t.anio IS NULL, t.anio, t.trimestre",
    },
    "mes": {
        "label": "Año y mes",
        "expression": (
            "CASE WHEN t.anio IS NULL OR t.mes IS NULL THEN 'Sin fecha' "
            "ELSE CAST(t.anio AS TEXT) || ' · ' || "
            "printf('%02d', t.mes) || ' ' || t.mes_nombre END"
        ),
        "order": "t.anio IS NULL, t.anio, t.mes IS NULL, t.mes",
    },
}

_FILTERS = {
    "anio": {
        "label": "Año",
        "expression": "coalesce(CAST(t.anio AS TEXT), 'Sin año')",
    },
    "fuente": {
        "label": "Dataset de origen",
        "expression": "u.dataset_origen",
    },
    "grupo": {
        "label": "Grupo taxonómico",
        "expression": "x.clase_grupo",
    },
    "provincia": {
        "label": "Provincia",
        "expression": "r.provincia",
    },
}

ANALISIS = {
    "q1-concentracion-territorial": {
        "row_levels": ["provincia", "municipio"],
        "column_levels": ["grupo", "clase", "familia", "especie"],
        "default_row": "provincia",
        "default_column": "grupo",
        "filters": ["anio", "fuente"],
        "chart_one": "records",
        "chart_one_sort": "rank",
        "chart_two": "species",
        "chart_two_axis": "column",
    },
    "q2-amenaza-taxon-fuente": {
        "row_levels": ["fuente"],
        "column_levels": ["codigo_iucn"],
        "default_row": "fuente",
        "default_column": "codigo_iucn",
        "filters": ["grupo", "provincia"],
        "chart_one": "records",
        "chart_one_sort": "rank",
        "chart_two": "risk",
        "chart_two_axis": "row",
    },
    "q3-crecimiento-temporal": {
        "row_levels": ["anio", "trimestre", "mes"],
        "column_levels": ["fuente"],
        "default_row": "anio",
        "default_column": "fuente",
        "filters": ["grupo", "provincia"],
        "chart_one": "records",
        "chart_one_sort": "axis",
        "chart_two": "species",
        "chart_two_axis": "column",
    },
    "q4-urbano-rural-amenaza": {
        "row_levels": ["categoria"],
        "column_levels": ["anio", "trimestre", "mes"],
        "default_row": "categoria",
        "default_column": "anio",
        "filters": ["fuente", "grupo"],
        "chart_one": "records",
        "chart_one_sort": "rank",
        "chart_two": "threat_rate",
        "chart_two_axis": "row",
    },
}


def _is_missing(value):
    return value is None or pd.isna(value) or (isinstance(value, str) and not value.strip())


def _text(value, default):
    return default if _is_missing(value) else str(value).strip()


def _integer(value):
    return None if _is_missing(value) else int(float(value))


def _dane(value):
    if _is_missing(value):
        return None
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value).strip()


def _unique_dimension(records):
    unique = sorted(
        set(records),
        key=lambda values: tuple("" if value is None else str(value) for value in values),
    )
    keys = {record: index for index, record in enumerate(unique, start=1)}
    return keys, [(keys[record], *record) for record in unique]


def normalizar_jerarquia_taxon(records):
    """Neutraliza relaciones padre-hijo ambiguas sin duplicar registros de hechos."""
    normalized = [list(record) for record in records]
    conflicts = set()
    child_names = {
        1: "clase",
        2: "familia",
        3: "género",
        4: "especie",
    }
    for child_index in range(4, 0, -1):
        parent_index = child_index - 1
        parents_by_child = {}
        for record in normalized:
            parents_by_child.setdefault(record[child_index], set()).add(
                record[parent_index]
            )
        ambiguous_children = {
            child
            for child, parents in parents_by_child.items()
            if len(parents) > 1
        }
        for child in ambiguous_children:
            conflicts.update(
                record[4]
                for record in normalized
                if record[child_index] == child
            )
            parent_value = f"No conciliado · {child_names[child_index]}: {child}"
            for record in normalized:
                if record[child_index] == child:
                    record[parent_index] = parent_value
    return [tuple(record) for record in normalized], conflicts


def _make_dimensions(source):
    time_records = [
        (
            _integer(row.year),
            _text(row.trimestre, "Sin Trimestre"),
            _integer(row.month),
            _text(row.mes_nombre, "Sin Mes"),
            _text(row.temporada_climatica, "Sin Determinar"),
        )
        for row in source[
            ["year", "trimestre", "month", "mes_nombre", "temporada_climatica"]
        ].itertuples(index=False)
    ]
    territory_records = [
        (
            _text(row.provincia, "Sin Clasificar"),
            _text(row.municipio, "Sin Clasificar"),
            _dane(row.codigo_dane),
            _text(row.categoria_territorial, "No Determinada"),
        )
        for row in source[
            ["provincia", "municipio", "codigo_dane", "categoria_territorial"]
        ].itertuples(index=False)
    ]
    raw_taxa = [
        (
            _text(row.clase_grupo, "Sin Identificar"),
            _text(row[1], "Sin Identificar"),
            _text(row.family, "Sin Identificar"),
            _text(row.genus, "Sin Identificar"),
            _text(row.scientificName, "Sin Identificar"),
        )
        for row in source[
            ["clase_grupo", "class", "family", "genus", "scientificName"]
        ].itertuples(index=False)
    ]
    normalized_taxa, conflicting_taxa = normalizar_jerarquia_taxon(raw_taxa)
    taxon_records = [
        (*record, _text(common_name, "Sin Registro"))
        for record, common_name in zip(normalized_taxa, source["nombre_comun"])
    ]
    source_records = [
        (
            _text(row.dataset_origen, "Sin Identificar"),
            _text(row.tipo_registro, "Sin Identificar"),
            _text(row.basisOfRecord, "Sin Identificar"),
        )
        for row in source[
            ["dataset_origen", "tipo_registro", "basisOfRecord"]
        ].itertuples(index=False)
    ]
    conservation_records = [
        (
            _text(row.iucn_codigo, "NE"),
            _text(row.iucn_estado, "No Evaluada (NE)"),
            _text(row.especie_amenazada, "Sin Evaluar / Datos Insuficientes"),
        )
        for row in source[
            ["iucn_codigo", "iucn_estado", "especie_amenazada"]
        ].itertuples(index=False)
    ]

    time_keys, time_rows = _unique_dimension(time_records)
    territory_keys, territory_rows = _unique_dimension(territory_records)
    taxon_keys, taxon_rows = _unique_dimension(taxon_records)
    source_keys, source_rows = _unique_dimension(source_records)
    conservation_keys, conservation_rows = _unique_dimension(conservation_records)

    return {
        "dim_tiempo": (time_keys, time_rows),
        "dim_territorio": (territory_keys, territory_rows),
        "dim_taxon": (taxon_keys, taxon_rows),
        "dim_fuente": (source_keys, source_rows),
        "dim_conservacion": (conservation_keys, conservation_rows),
        "taxon_fact_keys": [taxon_keys[record] for record in taxon_records],
        "conflicting_taxa": conflicting_taxa,
    }


def _create_schema(connection):
    connection.executescript(
        """
        CREATE TABLE dim_tiempo (
            tiempo_key INTEGER PRIMARY KEY,
            anio INTEGER,
            trimestre TEXT NOT NULL,
            mes INTEGER,
            mes_nombre TEXT NOT NULL,
            temporada_climatica TEXT NOT NULL,
            UNIQUE (anio, trimestre, mes, mes_nombre, temporada_climatica)
        );
        CREATE TABLE dim_territorio (
            territorio_key INTEGER PRIMARY KEY,
            provincia TEXT NOT NULL,
            municipio TEXT NOT NULL,
            codigo_dane TEXT,
            categoria_territorial TEXT NOT NULL,
            UNIQUE (provincia, municipio, codigo_dane, categoria_territorial)
        );
        CREATE TABLE dim_taxon (
            taxon_key INTEGER PRIMARY KEY,
            clase_grupo TEXT NOT NULL,
            clase TEXT NOT NULL,
            familia TEXT NOT NULL,
            genero TEXT NOT NULL,
            especie TEXT NOT NULL,
            nombre_comun TEXT NOT NULL,
            UNIQUE (clase_grupo, clase, familia, genero, especie, nombre_comun)
        );
        CREATE TABLE dim_fuente (
            fuente_key INTEGER PRIMARY KEY,
            dataset_origen TEXT NOT NULL,
            tipo_registro TEXT NOT NULL,
            basis_of_record TEXT NOT NULL,
            UNIQUE (dataset_origen, tipo_registro, basis_of_record)
        );
        CREATE TABLE dim_conservacion (
            conservacion_key INTEGER PRIMARY KEY,
            iucn_codigo TEXT NOT NULL,
            iucn_estado TEXT NOT NULL,
            grupo_amenaza TEXT NOT NULL,
            UNIQUE (iucn_codigo, iucn_estado, grupo_amenaza)
        );
        CREATE TABLE hecho_registros_ocurrencia (
            registro_key TEXT PRIMARY KEY,
            tiempo_key INTEGER NOT NULL REFERENCES dim_tiempo(tiempo_key),
            territorio_key INTEGER NOT NULL REFERENCES dim_territorio(territorio_key),
            taxon_key INTEGER NOT NULL REFERENCES dim_taxon(taxon_key),
            fuente_key INTEGER NOT NULL REFERENCES dim_fuente(fuente_key),
            conservacion_key INTEGER NOT NULL REFERENCES dim_conservacion(conservacion_key),
            cantidad_registros INTEGER NOT NULL CHECK (cantidad_registros >= 0),
            flag_amenazada INTEGER NOT NULL CHECK (flag_amenazada IN (0, 1)),
            flag_riesgo INTEGER NOT NULL CHECK (flag_riesgo IN (0, 1)),
            flag_no_evaluada INTEGER NOT NULL CHECK (flag_no_evaluada IN (0, 1))
        );
        CREATE INDEX ix_hecho_tiempo ON hecho_registros_ocurrencia(tiempo_key);
        CREATE INDEX ix_hecho_territorio ON hecho_registros_ocurrencia(territorio_key);
        CREATE INDEX ix_hecho_taxon ON hecho_registros_ocurrencia(taxon_key);
        CREATE INDEX ix_hecho_fuente ON hecho_registros_ocurrencia(fuente_key);
        CREATE INDEX ix_hecho_conservacion ON hecho_registros_ocurrencia(conservacion_key);
        CREATE VIEW v_registros_analitico AS
        SELECT h.registro_key,
               t.anio, t.trimestre, t.mes, t.mes_nombre, t.temporada_climatica,
               r.provincia, r.municipio, r.codigo_dane, r.categoria_territorial,
               x.clase_grupo, x.clase, x.familia, x.genero, x.especie, x.nombre_comun,
               u.dataset_origen, u.tipo_registro, u.basis_of_record,
               c.iucn_codigo, c.iucn_estado, c.grupo_amenaza,
               h.cantidad_registros, h.flag_amenazada, h.flag_riesgo,
               h.flag_no_evaluada
        FROM hecho_registros_ocurrencia h
        JOIN dim_tiempo t ON t.tiempo_key = h.tiempo_key
        JOIN dim_territorio r ON r.territorio_key = h.territorio_key
        JOIN dim_taxon x ON x.taxon_key = h.taxon_key
        JOIN dim_fuente u ON u.fuente_key = h.fuente_key
        JOIN dim_conservacion c ON c.conservacion_key = h.conservacion_key;
        """
    )


@lru_cache(maxsize=1)
def obtener_modelo():
    source = pd.read_csv(DATASET, encoding="utf-8-sig", low_memory=False)
    required = {
        "occurrenceID", "year", "trimestre", "month", "mes_nombre",
        "temporada_climatica", "provincia", "municipio", "codigo_dane",
        "categoria_territorial", "scientificName", "clase_grupo", "class",
        "family", "genus",         "nombre_comun", "fecha", "dataset_origen", "tipo_registro",
        "basisOfRecord", "iucn_codigo", "iucn_estado", "especie_amenazada",
        "cantidad_registros",
    }
    missing_columns = sorted(required.difference(source.columns))
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas en Dataset.csv: {', '.join(missing_columns)}")
    if source["occurrenceID"].isna().any():
        raise ValueError("Dataset.csv contiene registros sin occurrenceID.")
    if source["occurrenceID"].duplicated().any():
        raise ValueError("Dataset.csv contiene occurrenceID duplicados; la granularidad no es única.")

    dimensions = _make_dimensions(source)
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    _create_schema(connection)

    dimension_specs = [
        (
            "dim_tiempo",
            "tiempo_key, anio, trimestre, mes, mes_nombre, temporada_climatica",
        ),
        (
            "dim_territorio",
            "territorio_key, provincia, municipio, codigo_dane, categoria_territorial",
        ),
        (
            "dim_taxon",
            "taxon_key, clase_grupo, clase, familia, genero, especie, nombre_comun",
        ),
        (
            "dim_fuente",
            "fuente_key, dataset_origen, tipo_registro, basis_of_record",
        ),
        (
            "dim_conservacion",
            "conservacion_key, iucn_codigo, iucn_estado, grupo_amenaza",
        ),
    ]
    for table, columns in dimension_specs:
        rows = dimensions[table][1]
        placeholders = ", ".join("?" for _ in rows[0])
        connection.executemany(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            rows,
        )

    fact_rows = []
    for index, row in enumerate(source.itertuples(index=False)):
        time = (
            _integer(row.year),
            _text(row.trimestre, "Sin Trimestre"),
            _integer(row.month),
            _text(row.mes_nombre, "Sin Mes"),
            _text(row.temporada_climatica, "Sin Determinar"),
        )
        territory = (
            _text(row.provincia, "Sin Clasificar"),
            _text(row.municipio, "Sin Clasificar"),
            _dane(row.codigo_dane),
            _text(row.categoria_territorial, "No Determinada"),
        )
        source_record = (
            _text(row.dataset_origen, "Sin Identificar"),
            _text(row.tipo_registro, "Sin Identificar"),
            _text(row.basisOfRecord, "Sin Identificar"),
        )
        conservation = (
            _text(row.iucn_codigo, "NE"),
            _text(row.iucn_estado, "No Evaluada (NE)"),
            _text(row.especie_amenazada, "Sin Evaluar / Datos Insuficientes"),
        )
        code = _text(row.iucn_codigo, "NE")
        fact_rows.append(
            (
                str(row.occurrenceID),
                dimensions["dim_tiempo"][0][time],
                dimensions["dim_territorio"][0][territory],
                dimensions["taxon_fact_keys"][index],
                dimensions["dim_fuente"][0][source_record],
                dimensions["dim_conservacion"][0][conservation],
                1 if _is_missing(row.cantidad_registros) else int(row.cantidad_registros),
                int(code in {"CR", "EN", "VU"}),
                int(code in {"CR", "EN", "VU", "NT"}),
                int(code == "NE"),
            )
        )
    connection.executemany(
        """
        INSERT INTO hecho_registros_ocurrencia (
            registro_key, tiempo_key, territorio_key, taxon_key, fuente_key,
            conservacion_key, cantidad_registros, flag_amenazada, flag_riesgo,
            flag_no_evaluada
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        fact_rows,
    )
    connection.commit()

    source_total = len(source)
    source_quantity = int(
        source["cantidad_registros"].fillna(1).astype(int).sum()
    )
    with _LOCK:
        loaded = connection.execute(
            """
            SELECT COUNT(*) AS records, SUM(cantidad_registros) AS quantity,
                   SUM(flag_amenazada) AS threatened,
                   SUM(flag_riesgo) AS risk,
                   SUM(flag_no_evaluada) AS not_evaluated
            FROM hecho_registros_ocurrencia
            """
        ).fetchone()
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        dimension_counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table, _ in dimension_specs
        }
        duplicate_key_counts = {
            table: connection.execute(
                f"SELECT COUNT(*) - COUNT(DISTINCT {table.replace('dim_', '')}_key) FROM {table}"
            ).fetchone()[0]
            for table, _ in dimension_specs
        }
        taxonomy_conflicts_after_load = 0
        for parent, child in [
            ("clase_grupo", "clase"),
            ("clase", "familia"),
            ("familia", "genero"),
            ("genero", "especie"),
        ]:
            taxonomy_conflicts_after_load += connection.execute(
                f"""
                SELECT COUNT(*) FROM (
                    SELECT {child} FROM dim_taxon
                    GROUP BY {child}
                    HAVING COUNT(DISTINCT {parent}) > 1
                )
                """
            ).fetchone()[0]
        ambiguous_municipalities = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT municipio FROM dim_territorio
                GROUP BY municipio
                HAVING COUNT(DISTINCT provincia) > 1
            )
            """
        ).fetchone()[0]
        ambiguous_months = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT anio, mes FROM dim_tiempo
                GROUP BY anio, mes
                HAVING COUNT(DISTINCT trimestre) > 1
            )
            """
        ).fetchone()[0]
        identified_taxa = connection.execute(
            """
            SELECT COUNT(DISTINCT especie) FROM dim_taxon
            WHERE especie <> 'Sin Identificar'
            """
        ).fetchone()[0]
    validation = [
        {
            "name": "Registros de hechos = filas tratadas",
            "expected": source_total,
            "actual": loaded["records"],
            "ok": source_total == loaded["records"],
        },
        {
            "name": "Suma de cantidad_registros = suma del origen",
            "expected": source_quantity,
            "actual": loaded["quantity"],
            "ok": source_quantity == loaded["quantity"],
        },
        {
            "name": "occurrenceID únicos = registros de hechos",
            "expected": source["occurrenceID"].nunique(),
            "actual": loaded["records"],
            "ok": source["occurrenceID"].nunique() == loaded["records"],
        },
        {
            "name": "Claves foráneas huérfanas",
            "expected": 0,
            "actual": len(foreign_key_errors),
            "ok": not foreign_key_errors,
        },
        {
            "name": "Claves duplicadas en dimensiones",
            "expected": 0,
            "actual": sum(duplicate_key_counts.values()),
            "ok": not any(duplicate_key_counts.values()),
        },
        {
            "name": "Registros CR/EN/VU",
            "expected": int(source["iucn_codigo"].isin(["CR", "EN", "VU"]).sum()),
            "actual": loaded["threatened"],
            "ok": int(source["iucn_codigo"].isin(["CR", "EN", "VU"]).sum())
            == loaded["threatened"],
        },
        {
            "name": "Especies/nombres identificados distintos",
            "expected": int(source["scientificName"].nunique()),
            "actual": identified_taxa,
            "ok": int(source["scientificName"].nunique()) == identified_taxa,
        },
        {
            "name": "Relaciones ambiguas en jerarquía taxonómica tras normalizar",
            "expected": 0,
            "actual": taxonomy_conflicts_after_load,
            "ok": taxonomy_conflicts_after_load == 0,
        },
        {
            "name": "Municipios asociados a más de una provincia",
            "expected": 0,
            "actual": ambiguous_municipalities,
            "ok": ambiguous_municipalities == 0,
        },
        {
            "name": "Meses asociados a más de un trimestre dentro del año",
            "expected": 0,
            "actual": ambiguous_months,
            "ok": ambiguous_months == 0,
        },
    ]
    date_values = pd.to_datetime(source["fecha"], errors="coerce")
    summary = {
        "records": source_total,
        "quantity": source_quantity,
        "threatened": loaded["threatened"],
        "risk": loaded["risk"],
        "not_evaluated": loaded["not_evaluated"],
        "unknown_year": int(source["year"].isna().sum()),
        "unknown_month": int(source["month"].isna().sum()),
        "unknown_taxon_names": int(source["scientificName"].isna().sum()),
        "identified_taxa": identified_taxa,
        "conflicting_taxa": len(dimensions["conflicting_taxa"]),
        "unknown_territory": int(
            source["provincia"].isna().sum()
            + source["provincia"].eq("Sin Clasificar").sum()
        ),
        "year_min": int(source["year"].min()),
        "year_max": int(source["year"].max()),
        "date_min": date_values.min().strftime("%Y-%m-%d"),
        "date_max": date_values.max().strftime("%Y-%m-%d"),
        "dimensions": dimension_counts,
        "validation": validation,
        "all_valid": all(check["ok"] for check in validation),
    }
    return {"connection": connection, "summary": summary}


def _where_clause(connection, analysis, parameters):
    conditions = []
    values = []
    selected_filters = []
    for filter_name in analysis["filters"]:
        definition = _FILTERS[filter_name]
        options = [
            row[0]
            for row in connection.execute(
                f"SELECT DISTINCT {definition['expression']} {_JOINS} "
                f"ORDER BY {definition['expression']}"
            ).fetchall()
        ]
        selected = parameters.get(f"f_{filter_name}", "Todas")
        if selected != "Todas" and selected not in options:
            raise ConsultaInvalida(
                f"Valor no válido para el filtro {definition['label']}."
            )
        if selected != "Todas":
            conditions.append(f"{definition['expression']} = ?")
            values.append(selected)
        selected_filters.append(
            {
                "key": filter_name,
                "label": definition["label"],
                "value": selected,
                "options": options,
            }
        )
    return (
        (" WHERE " + " AND ".join(conditions) if conditions else ""),
        values,
        selected_filters,
    )


def _aggregate(connection, row_axis, column_axis, where, values):
    species_expr = (
        "COUNT(DISTINCT CASE WHEN x.especie <> 'Sin Identificar' "
        "THEN x.especie END)"
    )
    sql = f"""
        SELECT {row_axis['expression']} AS row_label,
               {column_axis['expression']} AS column_label,
               COUNT(*) AS records,
               SUM(h.cantidad_registros) AS quantity,
               {species_expr} AS species,
               SUM(h.flag_amenazada) AS threatened,
               SUM(h.flag_riesgo) AS risk,
               SUM(h.flag_no_evaluada) AS not_evaluated
        {_JOINS}
        {where}
        GROUP BY {row_axis['expression']}, {column_axis['expression']}
        ORDER BY records DESC, row_label, column_label
    """
    return [dict(row) for row in connection.execute(sql, values).fetchall()]


def _chart(connection, axis, metric, where, values, sort_by_axis=False):
    species_expr = (
        "COUNT(DISTINCT CASE WHEN x.especie <> 'Sin Identificar' "
        "THEN x.especie END)"
    )
    measures = {
        "records": ("COUNT(*)", "registros", "count"),
        "species": (species_expr, "especies distintas", "count"),
        "risk": ("SUM(h.flag_riesgo)", "registros en riesgo", "count"),
        "threat_rate": (
            "100.0 * SUM(h.flag_amenazada) / COUNT(*)",
            "% de registros CR/EN/VU",
            "percent",
        ),
        "threatened": ("SUM(h.flag_amenazada)", "registros CR/EN/VU", "count"),
    }
    expression, unit, value_type = measures[metric]
    sql = f"""
        SELECT {axis['expression']} AS label,
               COUNT(*) AS records,
               {expression} AS value,
               SUM(h.flag_amenazada) AS threatened
        {_JOINS}
        {where}
        GROUP BY {axis['expression']}
        ORDER BY {axis['order']}
    """
    records = [dict(row) for row in connection.execute(sql, values).fetchall()]
    if not sort_by_axis and metric != "threat_rate":
        records.sort(key=lambda row: (-row["value"], row["label"]))
    if sort_by_axis and axis["expression"].startswith("CASE WHEN t.anio"):
        records = records[-24:] if len(records) > 30 else records
    records = records[:30] if sort_by_axis else records[:12]
    maximum = max((float(row["value"] or 0) for row in records), default=0) or 1
    for row in records:
        value = float(row["value"] or 0)
        row["width"] = round(value * 100 / maximum, 1)
        row["display"] = f"{value:.1f}%" if value_type == "percent" else f"{int(value):,}"
    return {"unit": unit, "items": records}


def _matrix(rows, pivot):
    if pivot:
        row_key, column_key = "column_label", "row_label"
    else:
        row_key, column_key = "row_label", "column_label"
    visible_rows = rows[:40]
    row_labels = list(dict.fromkeys(row[row_key] for row in visible_rows))
    column_labels = list(dict.fromkeys(row[column_key] for row in visible_rows))
    values = {
        (row[row_key], row[column_key]): row
        for row in visible_rows
    }
    matrix_rows = []
    for row_label in row_labels:
        cells = []
        for column_label in column_labels:
            value = values.get((row_label, column_label))
            cells.append(
                {
                    "records": value["records"] if value else None,
                    "threatened": value["threatened"] if value else None,
                    "rate": (
                        round(100 * value["threatened"] / value["records"], 2)
                        if value and value["records"]
                        else None
                    ),
                }
            )
        matrix_rows.append({"label": row_label, "cells": cells})
    return column_labels, matrix_rows


def _comparar_periodos_equivalentes(connection, where, values):
    conditions = ["t.anio IN (2024, 2025)", "t.mes BETWEEN 1 AND 8"]
    period_where = (
        where + " AND " + " AND ".join(conditions)
        if where
        else " WHERE " + " AND ".join(conditions)
    )
    period_rows = connection.execute(
        f"""
        SELECT t.anio AS year, COUNT(*) AS records,
               COUNT(DISTINCT CASE WHEN x.especie <> 'Sin Identificar'
                   THEN x.especie END) AS species
        {_JOINS}
        {period_where}
        GROUP BY t.anio
        ORDER BY t.anio
        """,
        values,
    ).fetchall()
    missing_month_rows = connection.execute(
        f"""
        SELECT t.anio AS year, COUNT(*) AS records
        {_JOINS}
        {where + ' AND ' if where else ' WHERE '}t.anio IN (2024, 2025)
            AND t.mes IS NULL
        GROUP BY t.anio
        """,
        values,
    ).fetchall()
    periods = {row["year"]: dict(row) for row in period_rows}
    if 2024 not in periods or 2025 not in periods:
        return None
    missing_months = {
        row["year"]: row["records"] for row in missing_month_rows
    }
    baseline = periods[2024]["records"]
    change_pct = (
        100 * (periods[2025]["records"] - baseline) / baseline
        if baseline
        else None
    )
    return {
        "periods": periods,
        "missing_months": missing_months,
        "change_pct": change_pct,
    }


def _insights(
    rows,
    total_records,
    filters,
    row_label,
    column_label,
    period_comparison=None,
):
    if not rows:
        return []
    rows = rows[:40]
    active_filters = ", ".join(
        f"{item['label']}: {item['value']}"
        for item in filters
    )
    top_records = rows[0]
    species_candidates = [
        row
        for row in rows
        if (row["row_label"], row["column_label"])
        != (top_records["row_label"], top_records["column_label"])
    ]
    top_species = max(species_candidates or rows, key=lambda row: row["species"])
    top_share = (
        100 * top_records["records"] / total_records if total_records else 0
    )
    procedures = (
        f"Agrupación por {row_label} × {column_label}; "
        f"niveles y filtros activos: {active_filters or 'sin filtros'}."
    )
    common = {
        "dimensions": f"{row_label} × {column_label}",
        "procedure": procedures,
        "limitation": (
            "Los registros describen observaciones disponibles, no abundancia real "
            "ni esfuerzo de muestreo; no permiten inferir causalidad."
        ),
    }
    insights = [
        {
            **common,
            "question": "¿Qué combinación concentra más registros?",
            "evidence": (
                f"{top_records['row_label']} × {top_records['column_label']}: "
                f"{top_records['records']:,} registros de {total_records:,} "
                f"({top_share:.2f}% del total filtrado)."
            ),
            "finding": (
                f"La mayor celda de la matriz combina {top_records['row_label']} "
                f"con {top_records['column_label']} y reúne "
                f"{top_records['records']:,} registros."
            ),
            "interpretation": (
                "El cruce separa una concentración taxonómica-territorial (o de "
                "fuente/tiempo, según la vista) que el total agregado de etapa 4 "
                "no permite distinguir."
            ),
            "utility": (
                "Priorizar revisión de cobertura y metadatos de esa combinación "
                "antes de comparar territorios o asignar recursos."
            ),
        },
        {
            **common,
            "question": "¿En qué combinación se observa mayor riqueza taxonómica?",
            "evidence": (
                f"{top_species['row_label']} × {top_species['column_label']}: "
                f"{top_species['species']:,} especies distintas en "
                f"{top_species['records']:,} registros."
            ),
            "finding": (
                f"La riqueza máxima de la matriz corresponde a "
                f"{top_species['row_label']} × {top_species['column_label']} "
                f"({top_species['species']:,} especies distintas)."
            ),
            "interpretation": (
                "La riqueza y el volumen de observaciones no son intercambiables: "
                "el conteo distinto se recalcula en cada agrupación y no se suma "
                "entre celdas que puedan compartir especies."
            ),
            "utility": (
                "Usar el cruce como criterio de priorización exploratoria y "
                "contrastar después la cobertura de muestreo."
            ),
        },
    ]
    if period_comparison:
        first = period_comparison["periods"][2024]
        second = period_comparison["periods"][2025]
        change = period_comparison["change_pct"]
        missing_months = period_comparison["missing_months"]
        change_text = f"{change:+.2f}%" if change is not None else "no calculable"
        insights[1] = {
            **common,
            "question": (
                "¿Cómo cambió el volumen entre enero–agosto de 2024 y el mismo "
                "periodo de 2025?"
            ),
            "dimensions": "Tiempo (año y mes) × taxón/territorio (filtros activos)",
            "procedure": (
                f"Dice con {active_filters or 'sin filtros'}; conteo de ocurrencias "
                "para los meses 1–8 de ambos años. Se excluyen filas sin mes; 2026 "
                "se omite por ser parcial."
            ),
            "evidence": (
                f"2024: {first['records']:,} registros; 2025: {second['records']:,}; "
                f"variación = {change_text} respecto a 2024 "
                f"(denominador: {first['records']:,}). Sin mes en esos años: "
                f"{missing_months.get(2024, 0):,} y "
                f"{missing_months.get(2025, 0):,}, respectivamente."
            ),
            "finding": (
                f"En los mismos ocho meses, el subconjunto pasó de "
                f"{first['records']:,} a {second['records']:,} registros."
            ),
            "interpretation": (
                "La comparación de meses equivalentes evita contrastar un año "
                "completo con 2026 parcial; el cambio observado también puede reflejar "
                "variaciones de cobertura o esfuerzo de registro."
            ),
            "utility": (
                "Usar periodos comparables para seguimiento y revisar la mezcla de "
                "fuentes antes de atribuir el cambio a una tendencia biológica."
            ),
            "limitation": (
                "Se comparan solo registros con mes conocido en enero–agosto; el "
                "volumen no mide abundancia ni esfuerzo de muestreo."
            ),
        }
    return insights


def consultar_vista(slug, parameters):
    if slug not in ANALISIS:
        raise ConsultaInvalida("La pregunta de análisis no existe.")
    analysis = ANALISIS[slug]
    row_level = parameters.get("row_level", analysis["default_row"])
    column_level = parameters.get("column_level", analysis["default_column"])
    if row_level not in analysis["row_levels"] or column_level not in analysis["column_levels"]:
        raise ConsultaInvalida(
            "El nivel solicitado no pertenece a la jerarquía de esta pregunta."
        )
    pivot = parameters.get("pivot", "0")
    if pivot not in {"0", "1"}:
        raise ConsultaInvalida("El control de pivot debe ser 0 o 1.")

    model = obtener_modelo()
    connection = model["connection"]
    with _LOCK:
        where, values, filters = _where_clause(connection, analysis, parameters)
        summary_row = connection.execute(
            f"""
            SELECT COUNT(*) AS records,
                   SUM(h.cantidad_registros) AS quantity,
                   COUNT(DISTINCT CASE WHEN x.especie <> 'Sin Identificar'
                       THEN x.especie END) AS species,
                   SUM(h.flag_amenazada) AS threatened,
                   SUM(h.flag_riesgo) AS risk,
                   SUM(h.flag_no_evaluada) AS not_evaluated,
                   SUM(CASE WHEN t.anio IS NULL THEN 1 ELSE 0 END) AS unknown_year
            {_JOINS}
            {where}
            """,
            values,
        ).fetchone()
        rows = _aggregate(
            connection,
            _AXES[row_level],
            _AXES[column_level],
            where,
            values,
        )
        chart_one = _chart(
            connection,
            _AXES[row_level],
            analysis["chart_one"],
            where,
            values,
            sort_by_axis=analysis["chart_one_sort"] == "axis",
        )
        chart_two_level = (
            row_level if analysis["chart_two_axis"] == "row" else column_level
        )
        chart_two = _chart(
            connection,
            _AXES[chart_two_level],
            analysis["chart_two"],
            where,
            values,
        )
        period_comparison = (
            _comparar_periodos_equivalentes(connection, where, values)
            if slug == "q3-crecimiento-temporal"
            else None
        )

    summary = dict(summary_row)
    pivoted = pivot == "1"
    matrix_column_labels, matrix_rows = _matrix(rows, pivoted)
    matrix_rows = matrix_rows[:40]
    active_row = _AXES[column_level] if pivoted else _AXES[row_level]
    active_column = _AXES[row_level] if pivoted else _AXES[column_level]
    insight_rows = rows
    if pivoted:
        insight_rows = [
            {
                **row,
                "row_label": row["column_label"],
                "column_label": row["row_label"],
            }
            for row in rows
        ]
    result = {
        "summary": summary,
        "filters": filters,
        "row_levels": [
            {"key": level, "label": _AXES[level]["label"]}
            for level in analysis["row_levels"]
        ],
        "column_levels": [
            {"key": level, "label": _AXES[level]["label"]}
            for level in analysis["column_levels"]
        ],
        "row_level": row_level,
        "column_level": column_level,
        "row_label": active_row["label"],
        "column_label": active_column["label"],
        "chart_two_label": _AXES[chart_two_level]["label"],
        "chart_one": chart_one,
        "chart_two": chart_two,
        "matrix_column_labels": matrix_column_labels[:40],
        "matrix_rows": [
            {
                **row,
                "cells": row["cells"][:40],
            }
            for row in matrix_rows
        ],
        "matrix_truncated": len(rows) > 40,
        "pivot": pivoted,
        "insights": _insights(
            insight_rows,
            summary["records"],
            filters,
            active_row["label"],
            active_column["label"],
            period_comparison,
        ),
        "period_comparison": period_comparison,
    }
    return result
