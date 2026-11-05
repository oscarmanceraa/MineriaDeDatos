# Etapa 5 · Conocimientos multidimensionales P1 y P2

Este documento cubre únicamente las preguntas 1 y 2 de la Etapa 05. Las cifras se consultaron en `v_registros_analitico` el 4 de noviembre de 2026; no son valores precargados en las vistas. Las consultas SQL parametrizadas están en [`etapa5/sql/`](../../etapa5/sql/).

## Modelo, granularidad y medidas

El análisis reutiliza el hecho `hecho_registros_ocurrencia` y las dimensiones existentes de territorio, tiempo, taxón, fuente y conservación, expuestos por `v_registros_analitico`. La granularidad del hecho es una fila por `registro_key` de ocurrencia; las dimensiones se relacionan por claves únicas del modelo estrella.

- **Ocurrencias:** `COUNT(*)`, cantidad de filas del hecho. No equivale al número de individuos.
- **Cantidad de registros:** `SUM(cantidad_registros)`, medida aditiva que se reporta aparte del conteo de filas.
- **Promedio de cantidad:** `AVG(cantidad_registros)`, recalculado en cada agrupación; no se promedian promedios de grupos.
- **Especies identificadas:** `COUNT(DISTINCT especie)` excluyendo el valor explícito `Sin Identificar`. Los conteos únicos por celda pueden solaparse y no se suman para obtener un total.
- **Ocurrencias amenazadas:** `SUM(flag_amenazada)`, donde el ETL asigna 1 a códigos UICN CR, EN y VU. La tasa divide esta medida entre `COUNT(*)` del mismo corte. La participación sobre amenazadas divide entre la suma de CR/EN/VU del corte seleccionado.

`Sin Clasificar`, `Sin Identificar`, NE (No Evaluada), datos insuficientes y faltantes son estados/categorías distintos; no se interpretan como una respuesta negativa ni como ausencia de fauna. Las asociaciones observadas no prueban causalidad.

## Conocimientos de la pregunta 1

### 1. La cuota provincial depende del denominador territorial

- **Pregunta:** ¿Qué participación tiene la provincia con más ocurrencias y cómo cambia al incluir registros sin provincia?
- **Dimensiones y medidas:** Territorio (provincia); Tiempo y Taxón como filtros. Ocurrencias, suma de `cantidad_registros` y especies identificadas únicas.
- **Procedimiento:** Sin filtros de provincia, grupo o año, se agruparon las 20.087 filas por provincia con [`q1_grafico_territorio.sql`](../../etapa5/sql/q1_grafico_territorio.sql). Se calculó la cuota como ocurrencias de la provincia / ocurrencias de toda la selección; el grupo líder se contrastó con el resumen territorial de Etapa 4.
- **Evidencia:** Distrito Capital / Sabana tiene 5.078 ocurrencias. En el modelo completo, 5.078 / 20.087 = **25,28%**. Etapa 4 reportó 17.106 registros con territorio y 2.981 sin territorio; sobre el denominador territorial válido, 5.078 / 17.106 = **29,69%**.
- **Hallazgo:** El conteo del líder se mantiene, pero su participación baja cuando el denominador incorpora los registros sin provincia. No es un cambio en el numerador.
- **Interpretación frente a Etapa 4:** El resumen territorial de Etapa 4 mostraba concentración sobre los registros con territorio; esta vista hace explícito el efecto de incluir la categoría no clasificada y permite recalcular la cuota al filtrar.
- **Utilidad para una decisión:** Considerar la falta de asignación territorial al priorizar auditorías o muestreos, en vez de comparar porcentajes con denominadores distintos.
- **Limitación:** El volumen de ocurrencias depende también de cobertura y esfuerzo de observación; no mide abundancia biológica.

### 2. La mayor celda combina territorio y grupo taxonómico

- **Pregunta:** ¿Qué combinación de territorio y grupo taxonómico concentra más ocurrencias?
- **Dimensiones y medidas:** Territorio (provincia y municipio), Taxón (grupo taxonómico) y Tiempo (año). Ocurrencias, suma/promedio de `cantidad_registros` y especies identificadas únicas.
- **Procedimiento:** Con filtros vacíos y nivel provincia, se cruzaron provincia × grupo en [`q1_matriz.sql`](../../etapa5/sql/q1_matriz.sql). La consulta calcula porcentajes sobre el total de la selección y vuelve a calcular `AVG(cantidad_registros)` en cada celda.
- **Evidencia:** Distrito Capital / Sabana × Otros Invertebrados: **2.209 ocurrencias**, **248 especies identificadas únicas**, suma de `cantidad_registros` **2.209**, promedio **1,00** por ocurrencia y **11,00%** de 20.087. El resultado se reproduce con el pivot [`q1_pivot.sql`](../../etapa5/sql/q1_pivot.sql).
- **Hallazgo:** Una sola celda aporta el 11,00% de las ocurrencias generales; los totales provinciales de Etapa 4 no mostraban por sí solos esta combinación.
- **Interpretación frente a Etapa 4:** El cruce agrega la composición taxonómica al patrón territorial y permite localizar dónde se concentra el volumen conjunto. Describe asociación, no una causa ecológica.
- **Utilidad para una decisión:** Revisar taxonomía, cobertura y procedencia de la combinación antes de orientar allí una verificación o muestreo.
- **Limitación:** Las especies distintas de celdas diferentes pueden solaparse; las 248 especies de esta celda no se suman a las de otras celdas.

## Conocimientos de la pregunta 2

### 3. Una fuente aporta más de la mitad de las ocurrencias amenazadas

- **Pregunta:** ¿Qué fuente reúne más ocurrencias CR/EN/VU y qué proporción representa?
- **Dimensiones y medidas:** Fuente (`dataset_origen`) y Conservación (código/estado UICN); Taxón como filtro. Ocurrencias, ocurrencias CR/EN/VU, suma/promedio de `cantidad_registros` y especies amenazadas identificadas únicas.
- **Procedimiento:** Sin filtros de fuente ni grupo, se agruparon las filas por fuente con [`q2_grafico_fuentes.sql`](../../etapa5/sql/q2_grafico_fuentes.sql). La participación se recalculó como ocurrencias amenazadas de la fuente / todas las ocurrencias amenazadas del corte; también se calculó la tasa de la fuente como amenazas / ocurrencias de esa fuente.
- **Evidencia:** SiB Colombia / GBIF: **98 de 174** ocurrencias amenazadas, **56,32%** del total CR/EN/VU. En esa fuente hay 14.486 ocurrencias; su tasa CR/EN/VU es **0,68%** (98 / 14.486). El total de 174 se obtiene también de [`q2_indicadores.sql`](../../etapa5/sql/q2_indicadores.sql).
- **Hallazgo:** La fuente con mayor volumen amenazado concentra el 56,32% de esos registros, pero la tasa dentro de su propio volumen es 0,68%; participación y tasa responden preguntas distintas.
- **Interpretación frente a Etapa 4:** El cruce desglosa por fuente y diferencia la cuota del total amenazado de la tasa sobre el total de cada fuente, no inferible de un conteo global aislado.
- **Utilidad para una decisión:** Auditar consistencia, cobertura y métodos de las fuentes con mayor contribución antes de usar sus conteos para priorizar acciones.
- **Limitación:** Las diferencias de fuente pueden responder a esfuerzo o método de captura; el resultado no prueba mayor amenaza ecológica.

### 4. Mamíferos de SIBIO CAR concentran la mayor celda amenazada

- **Pregunta:** ¿Qué combinación de grupo taxonómico y fuente concentra más ocurrencias amenazadas?
- **Dimensiones y medidas:** Taxón (grupo), Fuente (`dataset_origen`) y Conservación (bandera CR/EN/VU y estado UICN). Ocurrencias, suma/promedio de cantidad y especies amenazadas identificadas únicas.
- **Procedimiento:** Sin filtros, se cruzaron grupo × fuente con [`q2_matriz.sql`](../../etapa5/sql/q2_matriz.sql). Se dividió cada celda amenazada entre el total de 174 ocurrencias CR/EN/VU, sin sumar porcentajes.
- **Evidencia:** Mamíferos × SIBIO CAR Cundinamarca: **76 de 174** amenazadas (**43,68%**); **196** ocurrencias en total en ese cruce, tasa CR/EN/VU **38,78%** (76 / 196), **3 especies amenazadas identificadas**, promedio de `cantidad_registros` **1,00**.
- **Hallazgo:** La celda aporta 43,68% de todas las ocurrencias amenazadas observadas en el corte, pero 38,78% de las ocurrencias del propio cruce son CR/EN/VU.
- **Interpretación frente a Etapa 4:** El cruce taxón × fuente aporta una combinación específica además de los perfiles agregados. Hay una discrepancia que impide una comparación directa con todos los artefactos de Etapa 4: `territorial.json` informa 174 amenazas, mientras `multivariada.json` informa 330. El conteo de la consulta actual coincide con el primer artefacto; la causa de la diferencia queda **POR CONFIRMAR**.
- **Utilidad para una decisión:** Priorizar la revisión de procedencia, estado UICN e identificación taxonómica en la celda con mayor volumen CR/EN/VU.
- **Limitación:** La celda no prueba que la fuente o el grupo causen la amenaza; el esfuerzo de muestreo y el solapamiento de especies entre fuentes no están controlados.

## Ejemplos de operaciones OLAP

Cada ejemplo se consultó nuevamente en el modelo. Los porcentajes indican explícitamente el denominador usado y las medidas se recalculan al cambiar el nivel o los filtros.

### Drill-down · Provincia a municipio

- **Dimensiones y medidas:** Territorio (provincia → municipio), Taxón (grupo); ocurrencias, cantidad, promedio, especies identificadas y porcentaje.
- **Nivel y filtros:** Provincia `Distrito Capital / Sabana`; todos los grupos y años; nivel municipio.
- **Procedimiento:** [`q1_drill_down.sql`](../../etapa5/sql/q1_drill_down.sql) agrupa municipio × grupo taxonómico dentro de la provincia seleccionada. El porcentaje de cada celda usa las **5.078 ocurrencias** de esa provincia como denominador.
- **Evidencia:** Bogotá, D.C. × Otros Invertebrados: **2.209** ocurrencias, **43,50%** de 5.078, suma **2.209**, promedio **1,00** y **248** especies identificadas únicas en la celda.
- **Interpretación:** El detalle municipal cambia la composición de la matriz y el denominador pasa del total general al total de la provincia seleccionada; el mayor conteo no significa mayor abundancia de individuos.

### Roll-up · Municipio a provincia

- **Dimensiones y medidas:** Territorio (municipio → provincia), Taxón (grupo); ocurrencias, cantidad, promedio, especies identificadas y porcentaje recalculado.
- **Nivel y filtros:** Mismo corte de la operación anterior: provincia `Distrito Capital / Sabana`, todos los grupos y años; nivel provincia.
- **Procedimiento:** [`q1_roll_up.sql`](../../etapa5/sql/q1_roll_up.sql) vuelve a agrupar los hechos en provincia × grupo, en lugar de sumar porcentajes o promedios de municipios.
- **Evidencia:** La provincia conserva **5.078** ocurrencias; la celda Distrito Capital / Sabana × Otros Invertebrados registra **2.209** (**43,50%** de las 5.078), suma **2.209**, promedio **1,00** y **248** especies únicas.
- **Interpretación:** El total de ocurrencias se conserva al volver al nivel provincial, pero las entidades únicas y los promedios se recalculan en el nivel solicitado.

### Slice · Año 2025

- **Dimensiones y medidas:** Tiempo (año), Territorio (provincia) y Taxón (grupo); ocurrencias, cantidad, promedio, especies y participación.
- **Nivel y filtros:** `anio = 2025`; todas las provincias y grupos.
- **Procedimiento:** [`q1_slice.sql`](../../etapa5/sql/q1_slice.sql) restringe primero el cubo al año y agrupa provincia × grupo. La participación de la celda usa como denominador las ocurrencias del año seleccionado.
- **Evidencia:** El corte contiene **7.993** ocurrencias; Distrito Capital / Sabana × Aves tiene **1.117** (**13,97%** de 7.993), promedio de cantidad **1,00**.
- **Interpretación:** El corte temporal cambia el conjunto y, por tanto, vuelve a calcular las cuotas; no se compara aquí con 2026, que es parcial, ni se afirma una tendencia interanual.

### Pivot · Intercambio de ejes territorio y taxón

- **Dimensiones y medidas:** Provincia × grupo taxonómico; ocurrencias, cantidad, promedio, especies y porcentaje de ocurrencias.
- **Nivel y filtros:** Todas las provincias, grupos y años; filas = grupo taxonómico y columnas = provincia.
- **Procedimiento:** [`q1_pivot.sql`](../../etapa5/sql/q1_pivot.sql) cambia los ejes y recalcula agregaciones sobre el mismo conjunto, en lugar de limitarse a cambiar el tipo de gráfico.
- **Evidencia:** Otros Invertebrados × Distrito Capital / Sabana vuelve a mostrar **2.209** ocurrencias, **11,00%** de 20.087, promedio **1,00** y **248** especies únicas.
- **Interpretación:** Pivot cambia la orientación de lectura; no cambia el hecho subyacente ni la definición del denominador.

### Slice · Solo estados CR/EN/VU

- **Dimensiones y medidas:** Conservación (slice CR/EN/VU), Taxón (grupo) y Fuente; ocurrencias amenazadas, suma/promedio de cantidad, especies únicas y participación.
- **Nivel y filtros:** `flag_amenazada = 1`, todas las fuentes y grupos.
- **Procedimiento:** [`q2_slice.sql`](../../etapa5/sql/q2_slice.sql) filtra por la bandera construida en el ETL y vuelve a agrupar grupo × fuente. La participación se calcula sobre las ocurrencias amenazadas incluidas en el corte.
- **Evidencia:** El slice deja **174** ocurrencias y **23** especies amenazadas identificadas únicas. Mamíferos × SIBIO CAR Cundinamarca aporta **76** (**43,68%** de 174); promedio de cantidad **1,00**.
- **Interpretación:** Al filtrar a CR/EN/VU, el denominador de participación es 174; la tasa de amenaza dentro del slice sería 100% por construcción y no debe usarse como comparación con el cubo completo.

### Dice · Fuente y grupo taxonómico, con desglose UICN

- **Dimensiones y medidas:** Fuente = `SIBIO CAR Cundinamarca`, Taxón = `Mamíferos`; desglose por código/estado de Conservación; ocurrencias, ocurrencias amenazadas, cantidad, promedio y porcentaje.
- **Nivel y filtros:** Fuente `SIBIO CAR Cundinamarca` y grupo `Mamíferos`; todos los estados UICN.
- **Procedimiento:** [`q2_dice.sql`](../../etapa5/sql/q2_dice.sql) restringe simultáneamente fuente y grupo, y agrupa por código/estado UICN. El porcentaje de cada fila usa como denominador las **196 ocurrencias** del corte dice.
- **Evidencia:** VU: **76** ocurrencias amenazadas, **38,78%** de 196; NE: **62**; LC: **58**. La suma es 196 y el promedio de cantidad en el corte es **1,00**. NE y LC no se convierten en estados negativos: representan categorías UICN diferentes.
- **Interpretación:** Dice reduce el cubo a una combinación concreta de fuente y taxón y permite inspeccionar su composición de conservación; las 76 VU son ocurrencias, no individuos.

## Limitaciones y asuntos POR CONFIRMAR

- El modelo mide registros de ocurrencia; no se dispone aquí de una medida de esfuerzo de muestreo que permita normalizar las comparaciones.
- Las categorías sin clasificar, sin identificar, NE, datos insuficientes y faltantes deben conservarse diferenciadas. `flag_amenazada = 0` no basta para etiquetar un registro como “no amenazado”.
- La serie temporal incluye 2026 parcial según el artefacto de Etapa 4; comparar periodos exige cortes equivalentes. El ejemplo de slice 2025 es una selección aislada, no una comparación temporal.
- **POR CONFIRMAR:** el artefacto `static/json/conocimiento/multivariada.json` informa 330 registros amenazados, mientras `static/json/conocimiento/territorial.json` y la consulta actual informan 174. No se conoce si difieren por definición, corte o proceso de generación; no se atribuye la diferencia a una causa.
- Los hallazgos son descriptivos. Asociación entre territorio, grupo, fuente y estado UICN no implica causalidad.
