from flask import Blueprint, render_template

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')


@main.route('/etapa-1')
def etapa1():
    return render_template('etapa1.html')