-- ANTES: nulos de campos núcleo en el staging
SELECT COUNT(*) AS total,
       SUM(CASE WHEN decimalLatitude  IS NULL OR LTRIM(RTRIM(decimalLatitude))  = '' THEN 1 ELSE 0 END) AS sin_lat,
       SUM(CASE WHEN decimalLongitude IS NULL OR LTRIM(RTRIM(decimalLongitude)) = '' THEN 1 ELSE 0 END) AS sin_lon,
       SUM(CASE WHEN eventDate IS NULL OR LTRIM(RTRIM(eventDate)) = '' THEN 1 ELSE 0 END) AS sin_fecha,
       SUM(CASE WHEN scientificName IS NULL OR LTRIM(RTRIM(scientificName)) = '' THEN 1 ELSE 0 END) AS sin_nombre
FROM Primero.GBIF_Original;

-- DESPUÉS: calidad en limpio
SELECT COUNT(*) AS total,
       SUM(CASE WHEN decimalLatitude  IS NULL THEN 1 ELSE 0 END) AS sin_lat,
       SUM(CASE WHEN decimalLongitude IS NULL THEN 1 ELSE 0 END) AS sin_lon,
       SUM(CASE WHEN eventDate IS NULL THEN 1 ELSE 0 END) AS sin_fecha,
       SUM(CASE WHEN scientificName IS NULL THEN 1 ELSE 0 END) AS sin_nombre
FROM limpio.GBIF;

-- DESPUÉS: coordenadas dentro del rango de Cundinamarca
SELECT COUNT(*) AS total,
       SUM(CASE WHEN decimalLatitude BETWEEN 3.5 AND 6.0
                 AND decimalLongitude BETWEEN -75.5 AND -72.5 THEN 1 ELSE 0 END) AS coord_ok
FROM limpio.GBIF;