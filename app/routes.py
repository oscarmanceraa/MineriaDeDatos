from flask import Blueprint, render_template, redirect, url_for

from app.calidad_data import RESULTADOS

main = Blueprint('main', __name__)

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
