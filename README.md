# MineriaDeDatos

Proyecto de minería de datos sobre la biodiversidad animal en Cundinamarca. La idea es comparar los registros de fauna entre zonas urbanas y rurales y ver qué tanto pesa el esfuerzo de observación humana en lo que aparece registrado.

El trabajo está dividido en etapas.

## Etapa 1 - Formulación

Aquí se define el problema, las preguntas de investigación, las necesidades de información, las fuentes y el diccionario de datos.

## Etapa 2 - Calidad de datos

Se hace el perfilamiento de los datasets, se evalúan las dimensiones de calidad (completitud, exactitud, consistencia, unicidad, validez y actualidad), se listan los problemas encontrados con sus posibles causas y se deja planteado el plan de tratamiento a seguir.

## Estructura del proyecto

- `app/`: la aplicación en Flask.
- `templates/`: las vistas.
- `static/`: hojas de estilo y gráficas.
- `scripts/`: scripts de perfilamiento y tratamiento.
- `Datasets/`: los archivos de datos (no se suben al repositorio).

## Cómo correrlo

```bash
pip install -r requirements.txt
python run.py
```

## Etapa 5 - Análisis multidimensional

La sección **Análisis multidimensional** usa el conjunto tratado `Dataset/Dataset.csv`
de las etapas anteriores. Al abrir la sección, la aplicación carga y valida un modelo
estrella en SQLite en memoria; las consultas de las cuatro preguntas se ejecutan sobre
esas tablas, sin depender de Supabase ni de credenciales para visualizar resultados.
El proceso de carga y el esquema SQL para Supabase siguen disponibles en
`etl/estrella/build_estrella.py` y `etl/estrella/schema.sql`.

La granularidad de `hecho_registros_ocurrencia` es una fila por `occurrenceID` tratado.
Sus claves foráneas enlazan `dim_tiempo`, `dim_territorio`, `dim_taxon`, `dim_fuente` y
`dim_conservacion`. Los atributos proceden de `year`, `trimestre`, `month`,
`temporada_climatica`; `provincia`, `municipio`, `codigo_dane`,
`categoria_territorial`; `clase_grupo`, `class`, `family`, `genus`,
`scientificName`, `nombre_comun`; `dataset_origen`, `tipo_registro`,
`basisOfRecord`; e `iucn_codigo`, `iucn_estado`, `especie_amenazada`.
Los valores faltantes se normalizan como categorías explícitas (por ejemplo, «Sin
Clasificar», «Sin Identificar» y «Sin año»), mientras `NE` se conserva como estado IUCN.
Cuando un nivel taxonómico aparece asociado con más de un padre, la transformación
etiqueta ese nivel como «No conciliado» para mantener funcionales las jerarquías
grupo–clase–familia–género–especie sin eliminar hechos.

Medidas principales: `COUNT(*)` cuenta ocurrencias; `SUM(cantidad_registros)` agrega
cantidades; `COUNT(DISTINCT especie)` calcula riqueza identificada en cada agrupación;
`SUM(flag_amenazada)` cuenta CR/EN/VU; y `SUM(flag_riesgo)` cuenta CR/EN/VU/NT.
La tasa CR/EN/VU es `registros CR/EN/VU / COUNT(*) × 100` del grupo mostrado. Riqueza
y porcentajes se recalculan al cambiar de nivel y no se suman entre grupos.

La carga valida unicidad de `occurrenceID`, conteos y cantidades contra el CSV,
uniones de claves foráneas, claves primarias de dimensiones y conteo de registros
CR/EN/VU. Las vistas permiten filtrar por dos dimensiones, drill-down, roll-up y pivot;
la matriz muestra como máximo 40 cruces de mayor volumen. La cobertura actual del
archivo es 2000–2026 con corte al 08/09/2026; 2026 es parcial. Los registros son
observaciones, no medidas de abundancia o esfuerzo, y las asociaciones no implican
causalidad. La vista temporal compara enero–agosto de 2024 y 2025 con el mismo
criterio de meses y excluye explícitamente los registros sin mes.
