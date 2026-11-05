SELECT
    iucn_codigo,
    iucn_estado,
    dataset_origen,
    COUNT(*) AS ocurrencias,
    COALESCE(SUM(cantidad_registros), 0) AS cantidad_registros,
    AVG(cantidad_registros) AS promedio_cantidad_por_ocurrencia,
    COALESCE(SUM(flag_amenazada), 0) AS ocurrencias_amenazadas,
    COUNT(DISTINCT CASE
        WHEN flag_amenazada = 1 AND especie <> 'Sin Identificar' THEN especie
    END) AS especies_amenazadas_identificadas,
    COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0)
        AS porcentaje_de_ocurrencias_en_corte
FROM v_registros_analitico
WHERE dataset_origen = %s
  AND clase_grupo = %s
  AND (%s::smallint IS NULL OR flag_amenazada = %s)
GROUP BY iucn_codigo, iucn_estado, dataset_origen
ORDER BY ocurrencias DESC, iucn_codigo, iucn_estado;
