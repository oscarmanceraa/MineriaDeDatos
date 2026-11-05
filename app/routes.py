import json
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, abort, render_template, redirect, request, url_for

from app.calidad_data import RESULTADOS
from app.modelo_estrella import (
    ANALISIS,
    ConsultaInvalida,
    consultar_vista,
    obtener_modelo,
)

main = Blueprint('main', __name__)


@lru_cache(maxsize=None)
def cargar_conocimiento(slug):
    ruta = Path(__file__).resolve().parent.parent / 'static' / 'json' / 'conocimiento' / f'{slug}.json'
    if not ruta.is_file():
        return {}
    return json.loads(ruta.read_text(encoding='utf-8'))

APARTADOS = [
    {'slug': 'problema-contexto', 'num': '01', 'titulo': 'Problema y contexto', 'disponible': True},
    {'slug': 'preguntas', 'num': '02', 'titulo': 'Pregunta principal y secundarias', 'disponible': True},
    {'slug': 'necesidades', 'num': '03', 'titulo': 'Necesidades de información', 'disponible': True},
    {'slug': 'fuentes', 'num': '04', 'titulo': 'Recolección y selección de fuentes', 'disponible': True},
    {'slug': 'dataset', 'num': '05', 'titulo': 'Dataset', 'disponible': True},
    {'slug': 'diccionario', 'num': '06', 'titulo': 'Diccionario de datos', 'disponible': True},
    {'slug': 'calidad', 'num': '07', 'titulo': 'Calidad inicial de los datos', 'disponible': True},
    {'slug': 'limitaciones', 'num': '08', 'titulo': 'Limitaciones y consideraciones', 'disponible': True},
]

DATASETS = [
    {'slug': 'gbif', 'num': '01', 'titulo': 'GBIF', 'inst': 'Global Biodiversity Information Facility', 'disponible': True},
    {'slug': 'iucn', 'num': '02', 'titulo': 'IUCN Red List', 'inst': 'International Union for Conservation of Nature', 'disponible': True},
    {'slug': 'sib-colombia', 'num': '03', 'titulo': 'SiB Colombia', 'inst': 'Instituto Humboldt', 'disponible': True},
    {'slug': 'naturalista', 'num': '04', 'titulo': 'NaturaLista Colombia', 'inst': 'iNaturalist / Instituto Humboldt', 'disponible': True},
    {'slug': 'sibio-car', 'num': '05', 'titulo': 'SIBIO CAR Cundinamarca', 'inst': 'CAR Cundinamarca', 'disponible': True},
    {'slug': 'datos-abiertos', 'num': '06', 'titulo': 'Datos Abiertos Cundinamarca', 'inst': 'Gobernación / DANE', 'disponible': True},
]

DATASETS_3 = [
    {'slug': 'gbif', 'num': '01', 'titulo': 'GBIF', 'inst': 'Global Biodiversity Information Facility', 'disponible': True},
    {'slug': 'iucn', 'num': '02', 'titulo': 'IUCN Red List', 'inst': 'International Union for Conservation of Nature', 'disponible': True},
    {'slug': 'naturalista', 'num': '03', 'titulo': 'NaturaLista Colombia', 'inst': 'iNaturalist / Instituto Humboldt', 'disponible': True},
    {'slug': 'sibio-car', 'num': '04', 'titulo': 'SIBIO CAR', 'inst': 'Sistema de Información sobre Biodiversidad de la CAR', 'disponible': True},
    {'slug': 'datos-abiertos', 'num': '05', 'titulo': 'Datos Abiertos Cundinamarca', 'inst': 'Gobernación / DANE', 'disponible': True},
]

CONOCIMIENTOS = [
    {'slug': 'poblacional', 'num': '01', 'titulo': 'Poblacional', 'inst': 'Composición y distribución de la población de registros.', 'disponible': True},
    {'slug': 'territorial', 'num': '02', 'titulo': 'Territorial', 'inst': 'Comparación entre territorios y concentración de registros.', 'disponible': True},
    {'slug': 'temporal', 'num': '03', 'titulo': 'Temporal', 'inst': 'Evolución y cambios a lo largo del periodo analizado.', 'disponible': True},
    {'slug': 'multivariada', 'num': '04', 'titulo': 'Multivariada', 'inst': 'Cruce de tres o más variables del conjunto de datos.', 'disponible': True},
]

DIMENSIONES = [
    {
        'slug': 'q1-concentracion-territorial',
        'num': '01',
        'titulo': '¿Cómo se distribuyen registros y riqueza de especies entre provincias y municipios según el grupo taxonómico?',
        'inst': 'Territorio · Taxón · Tiempo · Fuente',
        'disponible': True,
        'dimensions': 'Territorio y taxón; filtros de tiempo y fuente.',
        'measures': 'Registros de ocurrencia, especies distintas y registros CR/EN/VU.',
        'hierarchies': 'Provincia → municipio; grupo → clase → familia → especie.',
        'continuity': (
            'Etapa 4 mostró una fuerte concentración de registros en pocas provincias. '
            'Este cruce desagrega esa concentración por taxón y municipio, separando '
            'el volumen observado de la riqueza de especies.'
        ),
        'decision': (
            'Priorizar verificaciones de cobertura, georreferenciación e identificación '
            'en los cruces municipio–grupo con alta concentración o riqueza.'
        ),
        'limitation': (
            'El número de registros no estima abundancia ni esfuerzo de muestreo; '
            '2.981 filas están clasificadas como provincia Sin Clasificar. La fuente '
            'presenta relaciones taxonómicas ambiguas en algunos registros, que se '
            'muestran como «No conciliado».'
        ),
    },
    {
        'slug': 'q2-amenaza-taxon-fuente',
        'num': '02',
        'titulo': '¿Cómo cambian las categorías IUCN y los registros amenazados entre fuentes y grupos taxonómicos?',
        'inst': 'Fuente · Conservación · Taxón · Territorio',
        'disponible': True,
        'dimensions': 'Fuente y conservación; filtros de taxón y provincia.',
        'measures': 'Registros, CR/EN/VU, CR/EN/VU/NT y porcentaje sobre registros filtrados.',
        'hierarchies': 'Las categorías IUCN se comparan por código; el cambio de nivel se realiza en las jerarquías territorial, taxonómica y temporal de las otras preguntas.',
        'continuity': (
            'Etapa 4 encontró 330 registros en riesgo al incluir NT y una fuerte '
            'concentración de categorías no evaluadas. El cruce separa CR/EN/VU de NT '
            'y compara la composición de categorías entre fuentes.'
        ),
        'decision': (
            'Enfocar la revisión de metadatos de conservación y la búsqueda de '
            'evaluaciones vigentes en las combinaciones fuente–taxón con más registros '
            'sin evaluar o en riesgo.'
        ),
        'limitation': (
            'Una fuente con más registros no implica mayor amenaza ni mejor cobertura; '
            'la evaluación IUCN está asociada a especies y puede repetirse en ocurrencias.'
        ),
    },
    {
        'slug': 'q3-crecimiento-temporal',
        'num': '03',
        'titulo': '¿Cómo varían los registros por año, trimestre y mes según la fuente y el grupo taxonómico?',
        'inst': 'Tiempo · Fuente · Taxón · Territorio',
        'disponible': True,
        'dimensions': 'Tiempo y fuente; filtros de taxón y provincia.',
        'measures': 'Registros de ocurrencia, cantidad agregada y especies distintas.',
        'hierarchies': 'Año → trimestre → mes; fuente se compara por dataset de origen.',
        'continuity': (
            'Etapa 4 mostró el aumento reciente de registros y picos mensuales. '
            'Aquí se explora el nivel año/trimestre/mes cruzado con fuente, para '
            'distinguir qué parte del patrón acompaña cambios en la composición de fuentes. '
            'También compara enero–agosto de 2024 y 2025, el mismo periodo en ambos años.'
        ),
        'decision': (
            'Usar periodos y fuentes comparables al planear seguimiento; revisar primero '
            'si un pico coincide con un cambio de fuente o de tipo de registro.'
        ),
        'limitation': (
            '2026 solo tiene cobertura hasta el 08/09/2026 y no es comparable como año '
            'completo; 392 registros no tienen año y 445 no tienen mes. La comparación '
            'enero–agosto excluye los que no tienen mes; los cambios no prueban causalidad.'
        ),
    },
    {
        'slug': 'q4-urbano-rural-amenaza',
        'num': '04',
        'titulo': '¿Cómo varía la proporción CR/EN/VU entre categorías urbana y rural a lo largo del tiempo?',
        'inst': 'Territorio · Tiempo · Conservación · Fuente · Taxón',
        'disponible': True,
        'dimensions': 'Categoría territorial, tiempo y conservación (CR/EN/VU); filtros de fuente y taxón.',
        'measures': 'Registros CR/EN/VU y tasa sobre el total de registros de cada grupo.',
        'hierarchies': 'Año → trimestre → mes; categoría territorial urbana/rural/no determinada.',
        'continuity': (
            'Etapa 4 comparó conteos rurales y urbanos y detectó registros amenazados '
            'en ciertos territorios. Este análisis recalcula tasas con el denominador '
            'de cada cruce categoría–periodo y permite separar registros no clasificados.'
        ),
        'decision': (
            'Priorizar validación territorial y de conservación en periodos y categorías '
            'con mayores tasas observadas, sin interpretar esas tasas como riesgo causal.'
        ),
        'limitation': (
            'Las tasas describen registros etiquetados CR/EN/VU entre los registros '
            'filtrados, no riesgo de extinción local ni abundancia de fauna.'
        ),
    },
]


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/etapa-1')
def etapa1():
    return render_template('etapa1/index.html', apartados=APARTADOS)


@main.route('/etapa-1/<slug>')
def apartado(slug):
    item = next((a for a in APARTADOS if a['slug'] == slug), None)
    if not item or not item['disponible']:
        return redirect(url_for('main.etapa1'))

    idx = APARTADOS.index(item)
    nxt = next((a for a in APARTADOS[idx + 1:] if a['disponible']), None)
    return render_template('etapa1/r1-problema-datos.html', apartado=item, next=nxt)


@main.route('/etapa-2')
def etapa2():
    return render_template('etapa2/index.html', datasets=DATASETS)


@main.route('/etapa-2/<slug>')
def dataset(slug):
    item = next((d for d in DATASETS if d['slug'] == slug), None)
    if not item or not item['disponible']:
        return redirect(url_for('main.etapa2'))

    idx = DATASETS.index(item)
    nxt = next((d for d in DATASETS[idx + 1:] if d['disponible']), None)
    results = RESULTADOS.get(item['slug'], {})
    return render_template('etapa2/r2-calidad-datos.html', apartado=item, next=nxt, datasets=DATASETS, res=results)


@main.route('/etapa-3')
def etapa3():
    return render_template('etapa3/index.html', datasets=DATASETS_3)


@main.route('/etapa-3/<slug>')
def limpieza(slug):
    item = next((d for d in DATASETS_3 if d['slug'] == slug), None)
    if not item or not item['disponible']:
        return redirect(url_for('main.etapa3'))

    idx = DATASETS_3.index(item)
    nxt = next((d for d in DATASETS_3[idx + 1:] if d['disponible']), None)
    return render_template('etapa3/r3-limpieza-datos.html', apartado=item, next=nxt, datasets=DATASETS_3)


@main.route('/etapa-4')
def etapa4():
    return render_template('etapa4/index.html', conocimientos=CONOCIMIENTOS)


@main.route('/etapa-4/<slug>')
def conocimiento(slug):
    item = next((c for c in CONOCIMIENTOS if c['slug'] == slug), None)
    if not item or not item['disponible']:
        return redirect(url_for('main.etapa4'))

    idx = CONOCIMIENTOS.index(item)
    nxt = next((c for c in CONOCIMIENTOS[idx + 1:] if c['disponible']), None)
    res = cargar_conocimiento(item['slug'])
    return render_template(
        'etapa4/r4-conocimiento-evidente.html',
        apartado=item,
        next=nxt,
        conocimientos=CONOCIMIENTOS,
        res=res,
    )


@main.route('/etapa-5')
def etapa5():
    summary = obtener_modelo()['summary']
    return render_template(
        'etapa5/index.html',
        dimensiones=DIMENSIONES,
        modelo=summary,
    )


@main.route('/etapa-5/<slug>')
def analisis_multidimensional(slug):
    item = next((d for d in DIMENSIONES if d['slug'] == slug), None)
    if not item or not item['disponible']:
        return redirect(url_for('main.etapa5'))

    idx = DIMENSIONES.index(item)
    nxt = next((d for d in DIMENSIONES[idx + 1:] if d['disponible']), None)
    try:
        res = consultar_vista(slug, request.args)
    except ConsultaInvalida as error:
        abort(400, description=str(error))
    return render_template(
        'etapa5/r5-analisis-multidimensional.html',
        apartado=item,
        next=nxt,
        dimensiones=DIMENSIONES,
        analisis=ANALISIS[slug],
        res=res,
        modelo=obtener_modelo()['summary'],
    )
