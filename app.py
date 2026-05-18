import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import pytz

app = Flask(__name__)

def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(DATABASE_URL, sslmode='require', cursor_factory=RealDictCursor)
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect('banco.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS conviventes (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            status TEXT NOT NULL,
            foto TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS presencas (
            id SERIAL PRIMARY KEY,
            convivente_id INTEGER REFERENCES conviventes(id),
            data TEXT NOT NULL,
            presente BOOLEAN NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def get_brazil_time():
    tz = pytz.timezone('America/Sao_Paulo')
    return datetime.now(tz)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chamada')
def chamada():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    data_hoje = get_brazil_time().strftime('%Y-%m-%d')
    cur.execute('''
        SELECT c.id, c.nome, c.status, c.foto, p.presente
        FROM conviventes c
        LEFT JOIN presencas p ON c.id = p.convivente_id AND p.data = %s
        ORDER BY c.nome
    ''', (data_hoje,))
    conviventes = cur.fetchall()
    cur.close()
    conn.close()
    data_formatada = get_brazil_time().strftime('%d/%m/%Y')
    return render_template('chamada.html', conviventes=conviventes, data_hoje=data_formatada)

@app.route('/marcar_presenca/<int:id>', methods=['POST'])
def marcar_presenca(id):
    conn = get_db_connection()
    cur = conn.cursor()
    data_hoje = get_brazil_time().strftime('%Y-%m-%d')
    presente = 'presente' in request.form
    cur.execute('SELECT id FROM presencas WHERE convivente_id = %s AND data = %s', (id, data_hoje))
    existe = cur.fetchone()
    if existe:
        cur.execute('UPDATE presencas SET presente = %s WHERE convivente_id = %s AND data = %s', (presente, id, data_hoje))
    else:
        cur.execute('INSERT INTO presencas (convivente_id, data, presente) VALUES (%s, %s, %s)', (id, data_hoje, presente))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('chamada'))

@app.route('/conviventes')
def lista_conviventes():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, nome, status, foto FROM conviventes ORDER BY nome')
    conviventes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('conviventes.html', conviventes=conviventes)

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        status = request.form['status']
        foto = request.form.get('foto', '')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO conviventes (nome, status, foto) VALUES (%s, %s, %s)', (nome, status, foto))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('lista_conviventes'))
    return render_template('cadastrar.html')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        status = request.form['status']
        foto = request.form.get('foto', '')
        cur.execute('UPDATE conviventes SET nome = %s, status = %s, foto = %s WHERE id = %s', (nome, status, foto, id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('lista_conviventes'))
    cur.execute('SELECT id, nome, status, foto FROM conviventes WHERE id = %s', (id,))
    convivente = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('editar.html', convivente=convivente)

@app.route('/excluir/<int:id>')
def excluir(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM presencas WHERE convivente_id = %s', (id,))
    cur.execute('DELETE FROM conviventes WHERE id = %s', (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('lista_conviventes'))

@app.route('/relatorio_chamada')
def relatorio_chamada():
    return "<h1>Relatório em construção</h1><a href='/'>Voltar</a>"

@app.route('/relatorio_chamada_branco')
def relatorio_chamada_branco():
    return "<h1>Espelho em branco em construção</h1><a href='/'>Voltar</a>"

@app.route('/logout')
def logout():
    return "<h1>Logout em construção</h1><a href='/'>Voltar</a>"

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
