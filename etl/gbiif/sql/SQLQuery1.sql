USE GBIF;
-- Cuántos duplicados hay
SELECT COUNT(*) AS total, COUNT(DISTINCT occurrenceID) AS unicos,
       COUNT(*) - COUNT(DISTINCT occurrenceID) AS duplicados
FROM limpio.GBIF;

-- Eliminar duplicados conservando uno por occurrenceID
WITH d AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY occurrenceID ORDER BY (SELECT NULL)) AS rn
  FROM limpio.GBIF
)
DELETE FROM d WHERE rn > 1; 