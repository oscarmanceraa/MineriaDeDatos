SELECT
    clase_grupo,
    dataset_origen,
    COUNT(*) AS ocurrencias_amenazadas,
    COALESCE(SUM(cantidad_registros), 0) AS cantidad_registros,
    AVG(cantidad_registros) AS promedio_cantidad_por_ocurrencia,
    COUNT(DISTINCT CASE
        WHEN especie <> 'Sin Identificar' THEN especie
    END) AS especies_amenazadas_identificadas,
    COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0)
        AS porcentaje_del_total_amenazado
FROM v_registros_analitico
WHERE flag_amenazada = 1
  AND (%s::text IS NULL OR dataset_origen = %s)
  AND (%s::text IS NULL OR clase_grupo = %s)
GROUP BY clase_grupo, dataset_origen
ORDER BY ocurrencias_amenazadas DESC, clase_grupo, dataset_origen;
