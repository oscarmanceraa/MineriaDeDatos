import json
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, render_template, redirect, request, url_for

from app.calidad_data import RESULTADOS
from app.etapa5.q1_concentracion import q1_datos
from app.etapa5.q2_amenaza import q2_datos
from app.etapa5.q3_crecimiento import q3_datos
from app.etapa5.q4_urbano_rural import q4_datos

main = Blueprint('main', __name__)


@lru_cache(maxsize=None)
def cargar_conocimiento(slug):
    ruta = Path(__file__).resolve().parent.parent / 'static' / 'json' / 'conocimiento' / f'{slug}.json'
    if not ruta.is_file():
        return {}
    return json.loads(ruta.read_text(encoding='utf-8'))


@lru_cache(maxsize=None)
def cargar_conocimiento_oculto(slug):
    ruta = Path(__file__).resolve().parent.parent / 'static' / 'json' / 'conocimiento_oculto' / f'{slug}.json'
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
    {'slug': 'q1-concentracion-territorial', 'num': '01', 'titulo': '¿Dónde se concentran los registros y las especies al pasar de provincia a municipio?', 'inst': 'Territorio · Tiempo · Taxón', 'disponible': True},
    {'slug': 'q2-amenaza-taxon-fuente', 'num': '02', 'titulo': '¿Qué grupos taxonómicos y fuentes concentran los registros amenazados?', 'inst': 'Taxón · Conservación · Fuente', 'disponible': True},
    {'slug': 'q3-crecimiento-temporal', 'num': '03', 'titulo': '¿Qué explica el crecimiento de registros entre 2024 y 2026?', 'inst': 'Tiempo · Fuente · Taxón', 'disponible': True},
    {'slug': 'q4-urbano-rural-amenaza', 'num': '04', 'titulo': '¿Las provincias rurales concentran mayor tasa de amenaza que el área urbana?', 'inst': 'Territorio · Conservación · Tiempo', 'disponible': True},
]

SECCIONES_OCULTO = [
    {'slug': 'modelos-supervisados', 'num': '01', 'titulo': 'Modelos supervisados', 'inst': 'Predicción supervisada y comparación de tres modelos.', 'disponible': True},
    {'slug': 'clustering', 'num': '02', 'titulo': 'Clustering', 'inst': 'Agrupamiento y caracterización de patrones no evidentes.', 'disponible': True},
    {'slug': 'comentarios-youtube', 'num': '03', 'titulo': 'Comentarios de YouTube', 'inst': 'Extracción, limpieza y análisis de textos.', 'disponible': True},
    {'slug': 'conclusiones-integradas', 'num': '04', 'titulo': 'Conclusiones integradas', 'inst': 'Relación entre modelos, grupos y comentarios.', 'disponible': True},
    {'slug': 'informe-tecnico', 'num': '05', 'titulo': 'Informe técnico', 'inst': 'Documentación y evidencias de la etapa.', 'disponible': True},
    {'slug': 'video-sustentacion', 'num': '06', 'titulo': 'Video de sustentación', 'inst': 'Explicación de hallazgos y resultados principales.', 'disponible': True},
    {'slug': 'integracion-entrega', 'num': '07', 'titulo': 'Integración y entrega', 'inst': 'Aplicación Flask, repositorio y enlaces finales.', 'disponible': True},
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
    return render_template('etapa5/index.html', dimensiones=DIMENSIONES)


@main.route('/etapa-5/<slug>')
def analisis_multidimensional(slug):
    item = next((d for d in DIMENSIONES if d['slug'] == slug), None)
    if not item or not item['disponible']:
        return redirect(url_for('main.etapa5'))

    idx = DIMENSIONES.index(item)
    nxt = next((d for d in DIMENSIONES[idx + 1:] if d['disponible']), None)

    datos = None
    error = None
    if slug == 'q1-concentracion-territorial':
        try:
            datos = q1_datos(
                provincia=request.args.get('provincia'),
                grupo=request.args.get('grupo'),
                anio=request.args.get('anio'),
                nivel=request.args.get('nivel', 'provincia'),
                pivot=request.args.get('pivot') == '1',
                operacion=request.args.get('operacion'),
            )
        except Exception as exc:  # pragma: no cover - depende de Supabase
            error = str(exc)
    elif slug == 'q2-amenaza-taxon-fuente':
        try:
            datos = q2_datos(
                fuente=request.args.get('fuente'),
                grupo=request.args.get('grupo'),
                amenazadas=request.args.get('amenazadas') == '1',
                operacion=request.args.get('operacion'),
            )
        except Exception as exc:  # pragma: no cover - depende de Supabase
            error = str(exc)
    elif slug == 'q3-crecimiento-temporal':
        try:
            datos = q3_datos(
                fuente=request.args.get('fuente'),
                grupo=request.args.get('grupo'),
                nivel=request.args.get('nivel', 'anio'),
                pivot=request.args.get('pivot') == '1',
            )
        except Exception as exc:  # pragma: no cover - depende de Supabase
            error = str(exc)
    elif slug == 'q4-urbano-rural-amenaza':
        try:
            datos = q4_datos(
                provincia=request.args.get('provincia', 'todas'),
                periodo=request.args.get('periodo', 'todo'),
                categoria=request.args.get('categoria', 'Todas'),
                conservacion=request.args.get('conservacion', 'Todas'),
                pivot=request.args.get('pivot') == '1',
                drill=request.args.get('drill') == '1',
            )
        except Exception as exc:  # pragma: no cover - depende de Supabase
            error = str(exc)

    return render_template(
        'etapa5/r5-analisis-multidimensional.html',
        apartado=item,
        next=nxt,
        dimensiones=DIMENSIONES,
        datos=datos,
        error=error,
    )


@main.route('/etapa-6')
def etapa6():
    return render_template('etapa6/index.html', secciones=SECCIONES_OCULTO)


@main.route('/etapa-6/<slug>')
def conocimiento_oculto(slug):
    item = next((s for s in SECCIONES_OCULTO if s['slug'] == slug), None)
    if not item or not item['disponible']:
        return redirect(url_for('main.etapa6'))

    idx = SECCIONES_OCULTO.index(item)
    nxt = next((s for s in SECCIONES_OCULTO[idx + 1:] if s['disponible']), None)
    res = cargar_conocimiento_oculto(item['slug'])
    return render_template(
        'etapa6/r6-conocimiento-oculto.html',
        apartado=item,
        next=nxt,
        secciones=SECCIONES_OCULTO,
        res=res,
    )
