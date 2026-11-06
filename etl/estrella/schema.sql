drop view if exists v_registros_analitico;
drop table if exists hecho_registros_ocurrencia cascade;
drop table if exists dim_tiempo cascade;
drop table if exists dim_territorio cascade;
drop table if exists dim_taxon cascade;
drop table if exists dim_fuente cascade;
drop table if exists dim_conservacion cascade;

create table dim_tiempo (
    tiempo_key integer primary key,
    anio integer,
    trimestre text not null,
    mes integer,
    mes_nombre text not null,
    temporada_climatica text not null,
    constraint uq_dim_tiempo unique nulls not distinct
        (anio, trimestre, mes, mes_nombre, temporada_climatica)
);

create table dim_territorio (
    territorio_key integer primary key,
    provincia text not null,
    municipio text not null,
    codigo_dane text,
    categoria_territorial text not null,
    constraint uq_dim_territorio unique nulls not distinct
        (provincia, municipio, codigo_dane, categoria_territorial)
);

create table dim_taxon (
    taxon_key integer primary key,
    clase_grupo text not null,
    clase text not null,
    familia text not null,
    genero text not null,
    especie text not null,
    nombre_comun text not null,
    constraint uq_dim_taxon unique nulls not distinct
        (clase_grupo, clase, familia, genero, especie, nombre_comun)
);

create table dim_fuente (
    fuente_key integer primary key,
    dataset_origen text not null,
    tipo_registro text not null,
    basis_of_record text not null,
    constraint uq_dim_fuente unique nulls not distinct
        (dataset_origen, tipo_registro, basis_of_record)
);

create table dim_conservacion (
    conservacion_key integer primary key,
    iucn_codigo text not null,
    iucn_estado text not null,
    grupo_amenaza text not null,
    constraint uq_dim_conservacion unique nulls not distinct
        (iucn_codigo, iucn_estado, grupo_amenaza)
);

create table hecho_registros_ocurrencia (
    registro_key text primary key,
    tiempo_key integer not null references dim_tiempo (tiempo_key),
    territorio_key integer not null references dim_territorio (territorio_key),
    taxon_key integer not null references dim_taxon (taxon_key),
    fuente_key integer not null references dim_fuente (fuente_key),
    conservacion_key integer not null references dim_conservacion (conservacion_key),
    cantidad_registros integer not null default 1 check (cantidad_registros >= 0),
    flag_amenazada smallint not null default 0 check (flag_amenazada in (0, 1)),
    flag_riesgo smallint not null default 0 check (flag_riesgo in (0, 1)),
    flag_no_evaluada smallint not null default 0 check (flag_no_evaluada in (0, 1))
);

create index ix_hecho_tiempo on hecho_registros_ocurrencia (tiempo_key);
create index ix_hecho_territorio on hecho_registros_ocurrencia (territorio_key);
create index ix_hecho_taxon on hecho_registros_ocurrencia (taxon_key);
create index ix_hecho_fuente on hecho_registros_ocurrencia (fuente_key);
create index ix_hecho_conservacion on hecho_registros_ocurrencia (conservacion_key);

create view v_registros_analitico as
select
    f.registro_key,
    t.anio,
    t.trimestre,
    t.mes,
    t.mes_nombre,
    t.temporada_climatica,
    r.provincia,
    r.municipio,
    r.codigo_dane,
    r.categoria_territorial,
    x.clase_grupo,
    x.clase,
    x.familia,
    x.genero,
    x.especie,
    x.nombre_comun,
    u.dataset_origen,
    u.tipo_registro,
    u.basis_of_record,
    c.iucn_codigo,
    c.iucn_estado,
    c.grupo_amenaza,
    f.cantidad_registros,
    f.flag_amenazada,
    f.flag_riesgo,
    f.flag_no_evaluada
from hecho_registros_ocurrencia f
join dim_tiempo t using (tiempo_key)
join dim_territorio r using (territorio_key)
join dim_taxon x using (taxon_key)
join dim_fuente u using (fuente_key)
join dim_conservacion c using (conservacion_key);
