from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Pega a URL do banco direto do Render
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo do Convivente
class Convivente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    data_nascimento = db.Column(db.String(10))
    status = db.Column(db.String(20), default='Presente')

# Cria as tabelas no banco quando iniciar
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chamada')
def chamada():
    conviventes = Convivente.query.all()
    return render_template('chamada.html', conviventes=conviventes)

@app.route('/gerenciar_conviventes')
def gerenciar_conviventes():
    conviventes = Convivente.query.all()
    return render_template('gerenciar_conviventes.html', conviventes=conviventes)

@app.route('/relatorio')
def relatorio():
    return render_template('relatorio.html')

@app.route('/adicionar_convivente', methods=['POST'])
def adicionar_convivente():
    nome = request.form['nome']
    novo_convivente = Convivente(nome=nome)
    db.session.add(novo_convivente)
    db.session.commit()
    return redirect(url_for('gerenciar_conviventes'))

if __name__ == '__main__':
    app.run(debug=True)
