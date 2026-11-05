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
