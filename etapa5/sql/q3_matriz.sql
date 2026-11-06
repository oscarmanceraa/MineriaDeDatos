SELECT
    anio::text AS periodo,
    dataset_origen AS fuente,
    COUNT(*) AS ocurrencias,
    COALESCE(SUM(cantidad_registros), 0) AS cantidad_registros,
    AVG(cantidad_registros) AS promedio_cantidad_por_ocurrencia,
    COUNT(DISTINCT CASE
        WHEN especie <> 'Sin Identificar' THEN especie
    END) AS especies_identificadas,
    COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0) AS porcentaje_ocurrencias
FROM v_registros_analitico
WHERE anio BETWEEN 2024 AND 2026
  AND (%s::text IS NULL OR dataset_origen = %s)
  AND (%s::text IS NULL OR clase_grupo = %s)
GROUP BY anio, dataset_origen
ORDER BY anio, fuente;