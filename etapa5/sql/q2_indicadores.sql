SELECT
    COUNT(*) AS ocurrencias,
    COALESCE(SUM(cantidad_registros), 0) AS cantidad_registros,
    AVG(cantidad_registros) AS promedio_cantidad_por_ocurrencia,
    COALESCE(SUM(flag_amenazada), 0) AS ocurrencias_amenazadas,
    COUNT(DISTINCT CASE
        WHEN flag_amenazada = 1 AND especie <> 'Sin Identificar' THEN especie
    END) AS especies_amenazadas_identificadas,
    COALESCE(
        SUM(flag_amenazada) * 100.0 / NULLIF(COUNT(*), 0),
        0
    ) AS porcentaje_amenazadas
FROM v_registros_analitico
WHERE (%s::text IS NULL OR dataset_origen = %s)
  AND (%s::text IS NULL OR clase_grupo = %s)
  AND (%s::smallint IS NULL OR flag_amenazada = %s);
