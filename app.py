from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
import psycopg2.extras
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sisa_secreto_2026'

# Pega a URL do banco do Render
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS conviventes (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            quarto INTEGER NOT NULL,
            leito TEXT NOT NULL,
            foto TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chamadas (
            id SERIAL PRIMARY KEY,
            data TIMESTAMP NOT NULL,
            periodo TEXT NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS presencas (
            id SERIAL PRIMARY KEY,
            chamada_id INTEGER NOT NULL REFERENCES chamadas(id),
            convivente_id INTEGER NOT NULL REFERENCES conviventes(id),
            presente INTEGER NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

# Roda só 1x no deploy
with app.app_context():
    init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['logado'] = True
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu do sistema.')
    return redirect(url_for('login'))

@app.route('/conviventes')
def conviventes():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM conviventes ORDER BY quarto, leito')
    conviventes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('conviventes.html', conviventes=conviventes)

@app.route('/novo_convivente', methods=['GET', 'POST'])
def novo_convivente():
    fotos_dir = os.path.join(app.static_folder, 'fotos')
    fotos_disponiveis = []
    if os.path.exists(fotos_dir):
        fotos_disponiveis = [f for f in os.listdir(fotos_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    if request.method == 'POST':
        nome = request.form['nome']
        quarto = request.form['quarto']
        leito = request.form['leito']
        foto = request.form.get('foto', '')

        conn = get_db()
        cur = conn.cursor()
        cur.execute('INSERT INTO conviventes (nome, quarto, leito, foto) VALUES (%s,%s,%s,%s)',
                     (nome, quarto, leito, foto))
        conn.commit()
        cur.close()
        conn.close()
        flash('Convivente cadastrado!')
        return redirect(url_for('conviventes'))

    return render_template('novo_convivente.html', fotos=fotos_disponiveis)

@app.route('/editar_convivente/<int:id>', methods=['GET', 'POST'])
def editar_convivente(id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        nome = request.form['nome']
        quarto = request.form['quarto']
        leito = request.form['leito']
        cur.execute('UPDATE conviventes SET nome=%s, quarto=%s, leito=%s WHERE id=%s',
                     (nome, quarto, leito, id))
        conn.commit()
        cur.close()
        conn.close()
        flash('Convivente atualizado!')
        return redirect(url_for('conviventes'))

    cur.execute('SELECT * FROM conviventes WHERE id = %s', (id,))
    c = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('editar_convivente.html', c=c)

@app.route('/atualizar_convivente/<int:id>', methods=['GET', 'POST'])
def atualizar_convivente(id):
    return editar_convivente(id)

@app.route('/excluir_convivente/<int:id>')
def excluir_convivente(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM conviventes WHERE id = %s', (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Convivente excluído!')
    return redirect(url_for('conviventes'))

@app.route('/chamada')
def chamada():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM conviventes ORDER BY quarto, leito')
    conviventes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('chamada.html', conviventes=conviventes)

@app.route('/salvar_chamada', methods=['POST'])
def salvar_chamada():
    periodo = request.form['periodo']
    data = datetime.now()

    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO chamadas (data, periodo) VALUES (%s,%s) RETURNING id', (data, periodo))
    chamada_id = cur.fetchone()[0]

    for key, value in request.form.items():
        if key.startswith('presente_'):
            convivente_id = key.split('_')[1]
            presente = 1 if value == 'on' else 0
            cur.execute('INSERT INTO presencas (chamada_id, convivente_id, presente) VALUES (%s,%s,%s)',
                       (chamada_id, convivente_id, presente))

    conn.commit()
    cur.close()
    conn.close()
    flash('Chamada salva com sucesso!')
    return redirect(url_for('index'))

@app.route('/relatorios')
def relatorios():
    return render_template('relatorios.html')

@app.route('/relatorio_chamada')
def relatorio_chamada():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM chamadas ORDER BY data DESC')
    chamadas = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('relatorio_chamada.html', chamadas=chamadas)

@app.route('/relatorio_chamada_branco')
def relatorio_chamada_branco():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM conviventes ORDER BY quarto, leito')
    conviventes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('relatorio_chamada_branco.html', conviventes=conviventes)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
