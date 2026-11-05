SELECT
    provincia,
    municipio,
    clase_grupo,
    COUNT(*) AS ocurrencias,
    COALESCE(SUM(cantidad_registros), 0) AS cantidad_registros,
    AVG(cantidad_registros) AS promedio_cantidad_por_ocurrencia,
    COUNT(DISTINCT CASE
        WHEN especie <> 'Sin Identificar' THEN especie
    END) AS especies_identificadas,
    COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0) AS porcentaje_ocurrencias
FROM v_registros_analitico
WHERE provincia = %s
  AND (%s::text IS NULL OR clase_grupo = %s)
  AND (%s::integer IS NULL OR anio = %s)
GROUP BY provincia, municipio, clase_grupo
ORDER BY municipio, ocurrencias DESC, clase_grupo;
