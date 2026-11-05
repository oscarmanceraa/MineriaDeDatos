"""Construye el modelo estrella de la Etapa 05 en Supabase.

Fuente: Dataset/Dataset.csv (20.087 registros de ocurrencia tratados).
Destino: tablas dim_* y hecho_registros_ocurrencia en Supabase (PostgreSQL).

Uso:
    python etl/estrella/build_estrella.py            # crea esquema y carga
    python etl/estrella/build_estrella.py --dry-run  # solo valida el ETL en memoria

La cadena de conexion se lee de SUPABASE_DB_URL en el archivo .env de la raiz.
"""

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "Dataset" / "Dataset.csv"
SCHEMA = Path(__file__).resolve().parent / "schema.sql"
RESULTS = BASE / "results" / "estrella"

AMENAZADAS = {"CR", "EN", "VU"}
RIESGO = {"CR", "EN", "VU", "NT"}

load_dotenv(BASE / ".env")


def get_connection():
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise SystemExit("Falta SUPABASE_DB_URL en el archivo .env de la raiz.")
    return psycopg2.connect(url, connect_timeout=20)


def int_or_none(value):
    return None if pd.isna(value) else int(value)


def normalizar_dane(serie):
    def uno(value):
        if pd.isna(value):
            return None
        try:
            return str(int(float(value)))
        except (TypeError, ValueError):
            return str(value).strip()

    return serie.map(uno)


def construir_dimension(df, columnas, nombre_key):
    llave = (
        df[columnas]
        .astype("string")
        .fillna("__NA__")
        .agg("|".join, axis=1)
    )
    codigos, _ = pd.factorize(llave, sort=True)
    temporal = df[columnas].copy()
    temporal[nombre_key] = codigos + 1
    dim = (
        temporal.drop_duplicates(subset=[nombre_key])
        .sort_values(nombre_key)
        .reset_index(drop=True)
    )
    return dim, codigos + 1


def preparar(df):
    df = df.copy()

    tiempo = pd.DataFrame(
        {
            "anio": df["year"].astype("Int64"),
            "trimestre": df["trimestre"].fillna("Sin Trimestre"),
            "mes": df["month"].astype("Int64"),
            "mes_nombre": df["mes_nombre"].fillna("Sin Mes"),
            "temporada_climatica": df["temporada_climatica"].fillna("Sin Determinar"),
        }
    )
    dim_tiempo, df["tiempo_key"] = construir_dimension(
        tiempo, list(tiempo.columns), "tiempo_key"
    )

    territorio = pd.DataFrame(
        {
            "provincia": df["provincia"].fillna("Sin Clasificar"),
            "municipio": df["municipio"].fillna("Sin Clasificar"),
            "codigo_dane": normalizar_dane(df["codigo_dane"]),
            "categoria_territorial": df["categoria_territorial"].fillna(
                "No Determinada"
            ),
        }
    )
    dim_territorio, df["territorio_key"] = construir_dimension(
        territorio, list(territorio.columns), "territorio_key"
    )

    taxon = pd.DataFrame(
        {
            "especie": df["scientificName"].fillna("Sin Identificar"),
            "clase_grupo": df["clase_grupo"].fillna("Sin Identificar"),
            "clase": df["class"].fillna("Sin Identificar"),
            "familia": df["family"].fillna("Sin Identificar"),
            "genero": df["genus"].fillna("Sin Identificar"),
            "nombre_comun": df["nombre_comun"].fillna("Sin Registro"),
        }
    )
    dim_taxon = (
        taxon.drop_duplicates(subset=["especie"])
        .sort_values("especie")
        .reset_index(drop=True)
    )
    dim_taxon.insert(0, "taxon_key", range(1, len(dim_taxon) + 1))
    mapa_taxon = dict(zip(dim_taxon["especie"], dim_taxon["taxon_key"]))
    df["taxon_key"] = taxon["especie"].map(mapa_taxon)

    fuente = pd.DataFrame(
        {
            "dataset_origen": df["dataset_origen"].fillna("Sin Identificar"),
            "tipo_registro": df["tipo_registro"].fillna("Sin Identificar"),
            "basis_of_record": df["basisOfRecord"].fillna("Sin Identificar"),
        }
    )
    dim_fuente, df["fuente_key"] = construir_dimension(
        fuente, list(fuente.columns), "fuente_key"
    )

    conservacion = pd.DataFrame(
        {
            "iucn_codigo": df["iucn_codigo"].fillna("NE"),
            "iucn_estado": df["iucn_estado"].fillna("No Evaluada (NE)"),
            "grupo_amenaza": df["especie_amenazada"].fillna(
                "Sin Evaluar / Datos Insuficientes"
            ),
        }
    )
    dim_conservacion, df["conservacion_key"] = construir_dimension(
        conservacion, list(conservacion.columns), "conservacion_key"
    )

    df["cantidad_registros"] = df["cantidad_registros"].fillna(1).astype(int)
    df["flag_amenazada"] = df["iucn_codigo"].isin(AMENAZADAS).astype(int)
    df["flag_riesgo"] = df["iucn_codigo"].isin(RIESGO).astype(int)
    df["flag_no_evaluada"] = (df["iucn_codigo"] == "NE").astype(int)

    return df, dim_tiempo, dim_territorio, dim_taxon, dim_fuente, dim_conservacion


def registros_dim_tiempo(dim):
    return [
        (
            int(r.tiempo_key),
            int_or_none(r.anio),
            str(r.trimestre),
            int_or_none(r.mes),
            str(r.mes_nombre),
            str(r.temporada_climatica),
        )
        for r in dim.itertuples(index=False)
    ]


def registros_dim_territorio(dim):
    return [
        (
            int(r.territorio_key),
            str(r.provincia),
            str(r.municipio),
            None if pd.isna(r.codigo_dane) else str(r.codigo_dane),
            str(r.categoria_territorial),
        )
        for r in dim.itertuples(index=False)
    ]


def registros_dim_taxon(dim):
    return [
        (
            int(r.taxon_key),
            str(r.clase_grupo),
            str(r.clase),
            str(r.familia),
            str(r.genero),
            str(r.especie),
            str(r.nombre_comun),
        )
        for r in dim.itertuples(index=False)
    ]


def registros_dim_fuente(dim):
    return [
        (
            int(r.fuente_key),
            str(r.dataset_origen),
            str(r.tipo_registro),
            str(r.basis_of_record),
        )
        for r in dim.itertuples(index=False)
    ]


def registros_dim_conservacion(dim):
    return [
        (
            int(r.conservacion_key),
            str(r.iucn_codigo),
            str(r.iucn_estado),
            str(r.grupo_amenaza),
        )
        for r in dim.itertuples(index=False)
    ]


def registros_hecho(df):
    return [
        (
            str(r.occurrenceID),
            int(r.tiempo_key),
            int(r.territorio_key),
            int(r.taxon_key),
            int(r.fuente_key),
            int(r.conservacion_key),
            int(r.cantidad_registros),
            int(r.flag_amenazada),
            int(r.flag_riesgo),
            int(r.flag_no_evaluada),
        )
        for r in df[
            [
                "occurrenceID",
                "tiempo_key",
                "territorio_key",
                "taxon_key",
                "fuente_key",
                "conservacion_key",
                "cantidad_registros",
                "flag_amenazada",
                "flag_riesgo",
                "flag_no_evaluada",
            ]
        ].itertuples(index=False)
    ]


def cargar(conn, df, dims):
    dim_tiempo, dim_territorio, dim_taxon, dim_fuente, dim_conservacion = dims

    with conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA.read_text(encoding="utf-8"))
            execute_values(
                cur,
                "insert into dim_tiempo "
                "(tiempo_key, anio, trimestre, mes, mes_nombre, temporada_climatica) "
                "values %s",
                registros_dim_tiempo(dim_tiempo),
                page_size=1000,
            )
            execute_values(
                cur,
                "insert into dim_territorio "
                "(territorio_key, provincia, municipio, codigo_dane, categoria_territorial) "
                "values %s",
                registros_dim_territorio(dim_territorio),
                page_size=1000,
            )
            execute_values(
                cur,
                "insert into dim_taxon "
                "(taxon_key, clase_grupo, clase, familia, genero, especie, nombre_comun) "
                "values %s",
                registros_dim_taxon(dim_taxon),
                page_size=1000,
            )
            execute_values(
                cur,
                "insert into dim_fuente "
                "(fuente_key, dataset_origen, tipo_registro, basis_of_record) "
                "values %s",
                registros_dim_fuente(dim_fuente),
                page_size=1000,
            )
            execute_values(
                cur,
                "insert into dim_conservacion "
                "(conservacion_key, iucn_codigo, iucn_estado, grupo_amenaza) "
                "values %s",
                registros_dim_conservacion(dim_conservacion),
                page_size=1000,
            )
            execute_values(
                cur,
                "insert into hecho_registros_ocurrencia "
                "(registro_key, tiempo_key, territorio_key, taxon_key, fuente_key, "
                "conservacion_key, cantidad_registros, flag_amenazada, flag_riesgo, "
                "flag_no_evaluada) values %s",
                registros_hecho(df),
                page_size=1000,
            )


def validar(conn, df, dims):
    dim_tiempo, dim_territorio, dim_taxon, dim_fuente, dim_conservacion = dims
    checks = []

    def check(nombre, esperado, obtenido, detalle=""):
        checks.append(
            {
                "validacion": nombre,
                "esperado": esperado,
                "obtenido": obtenido,
                "ok": esperado == obtenido,
                "detalle": detalle,
            }
        )

    with conn.cursor() as cur:
        cur.execute("select count(*) from hecho_registros_ocurrencia")
        check("total de hechos = registros fuente", len(df), cur.fetchone()[0])

        cur.execute(
            "select coalesce(sum(cantidad_registros), 0) from hecho_registros_ocurrencia"
        )
        check(
            "suma de cantidad_registros",
            int(df["cantidad_registros"].sum()),
            int(cur.fetchone()[0]),
        )

        cur.execute(
            "select count(distinct registro_key) from hecho_registros_ocurrencia"
        )
        check("occurrenceID unico", len(df), cur.fetchone()[0])

        for tabla, columna in [
            ("dim_tiempo", "tiempo_key"),
            ("dim_territorio", "territorio_key"),
            ("dim_taxon", "taxon_key"),
            ("dim_fuente", "fuente_key"),
            ("dim_conservacion", "conservacion_key"),
        ]:
            cur.execute(
                f"select count(*) from (select {columna} from {tabla} "
                f"group by {columna} having count(*) > 1) duplicados"
            )
            check(f"claves unicas en {tabla}", 0, cur.fetchone()[0])

        for tabla, columna in [
            ("dim_tiempo", "tiempo_key"),
            ("dim_territorio", "territorio_key"),
            ("dim_taxon", "taxon_key"),
            ("dim_fuente", "fuente_key"),
            ("dim_conservacion", "conservacion_key"),
        ]:
            cur.execute(
                f"select count(*) from hecho_registros_ocurrencia h "
                f"left join {tabla} d using ({columna}) "
                f"where d.{columna} is null"
            )
            check(f"FK sin huerfanas hacia {tabla}", 0, cur.fetchone()[0])

        cur.execute(
            "select count(*) from hecho_registros_ocurrencia where flag_amenazada = 1"
        )
        check(
            "registros amenazados CR/EN/VU",
            int(df["iucn_codigo"].isin(AMENAZADAS).sum()),
            cur.fetchone()[0],
        )

        cur.execute(
            "select count(*) from hecho_registros_ocurrencia where flag_riesgo = 1"
        )
        check(
            "registros en riesgo CR/EN/VU/NT",
            int(df["iucn_codigo"].isin(RIESGO).sum()),
            cur.fetchone()[0],
        )

        cur.execute(
            "select count(distinct x.especie) from hecho_registros_ocurrencia h "
            "join dim_taxon x using (taxon_key) where x.especie <> 'Sin Identificar'"
        )
        check(
            "especies distintas",
            int(df["scientificName"].nunique()),
            cur.fetchone()[0],
        )

        cur.execute(
            "select r.provincia, count(*) from hecho_registros_ocurrencia h "
            "join dim_territorio r using (territorio_key) group by r.provincia"
        )
        modelo_prov = dict(cur.fetchall())

    origen_prov = (
        df["provincia"].fillna("Sin Clasificar").value_counts().astype(int).to_dict()
    )
    diferencias = {
        provincia: modelo_prov.get(provincia, 0) - origen_prov.get(provincia, 0)
        for provincia in set(modelo_prov) | set(origen_prov)
        if modelo_prov.get(provincia, 0) != origen_prov.get(provincia, 0)
    }
    checks.append(
        {
            "validacion": "conteos por provincia iguales a la fuente",
            "esperado": 0,
            "obtenido": len(diferencias),
            "ok": len(diferencias) == 0,
            "detalle": "provincias con diferencia: "
            + (", ".join(sorted(diferencias)) if diferencias else "ninguna"),
        }
    )

    resultados = {
        "generado": pd.Timestamp.now(tz="UTC").isoformat(),
        "registros_fuente": len(df),
        "registros_modelo": len(df),
        "dimensiones": {
            "dim_tiempo": len(dim_tiempo),
            "dim_territorio": len(dim_territorio),
            "dim_taxon": len(dim_taxon),
            "dim_fuente": len(dim_fuente),
            "dim_conservacion": len(dim_conservacion),
        },
        "checks": checks,
        "todo_ok": all(c["ok"] for c in checks),
    }
    return resultados


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepara y cuenta sin escribir en Supabase.",
    )
    args = parser.parse_args()

    df = pd.read_csv(DATA, encoding="utf-8-sig", low_memory=False)
    df, dim_tiempo, dim_territorio, dim_taxon, dim_fuente, dim_conservacion = preparar(
        df
    )
    dims = (dim_tiempo, dim_territorio, dim_taxon, dim_fuente, dim_conservacion)

    print(f"Registros fuente: {len(df):,}")
    print(f"dim_tiempo: {len(dim_tiempo):,}")
    print(f"dim_territorio: {len(dim_territorio):,}")
    print(f"dim_taxon: {len(dim_taxon):,}")
    print(f"dim_fuente: {len(dim_fuente):,}")
    print(f"dim_conservacion: {len(dim_conservacion):,}")

    if args.dry_run:
        print("Dry-run: no se escribio nada en Supabase.")
        return

    conn = get_connection()
    try:
        cargar(conn, df, dims)
        resultados = validar(conn, df, dims)
    finally:
        conn.close()

    RESULTS.mkdir(parents=True, exist_ok=True)
    salida = RESULTS / "validacion.json"
    salida.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nValidaciones:")
    for c in resultados["checks"]:
        estado = "OK" if c["ok"] else "FALLA"
        print(f"  [{estado}] {c['validacion']}: {c['obtenido']}")
    print(f"\nResultado global: {'OK' if resultados['todo_ok'] else 'CON FALLAS'}")
    print(f"Reporte: {salida}")


if __name__ == "__main__":
    main()
