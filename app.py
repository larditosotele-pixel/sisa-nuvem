from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sisa_secreto_2026'

DB_PATH = 'sisa.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS conviventes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            quarto INTEGER NOT NULL,
            leito INTEGER NOT NULL,
            foto TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chamadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            periodo TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS presencas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chamada_id INTEGER NOT NULL,
            convivente_id INTEGER NOT NULL,
            presente INTEGER NOT NULL,
            FOREIGN KEY (chamada_id) REFERENCES chamadas (id),
            FOREIGN KEY (convivente_id) REFERENCES conviventes (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/conviventes')
def conviventes():
    conn = get_db()
    conviventes = conn.execute('SELECT * FROM conviventes ORDER BY quarto, leito').fetchall()
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
        conn.execute('INSERT INTO conviventes (nome, quarto, leito, foto) VALUES (?,?,?,?)',
                     (nome, quarto, leito, foto))
        conn.commit()
        conn.close()
        flash('Convivente cadastrado!')
        return redirect(url_for('conviventes'))

    return render_template('novo_convivente.html', fotos=fotos_disponiveis)

@app.route('/editar_convivente/<int:id>', methods=['GET', 'POST'])
def editar_convivente(id):
    conn = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        quarto = request.form['quarto']
        leito = request.form['leito']
        conn.execute('UPDATE conviventes SET nome=?, quarto=?, leito=? WHERE id=?',
                     (nome, quarto, leito, id))
        conn.commit()
        conn.close()
        flash('Convivente atualizado!')
        return redirect(url_for('conviventes'))

    c = conn.execute('SELECT * FROM conviventes WHERE id =?', (id,)).fetchone()
    conn.close()
    return render_template('editar_convivente.html', c=c)

@app.route('/atualizar_convivente/<int:id>', methods=['GET', 'POST'])
def atualizar_convivente(id):
    return editar_convivente(id)

@app.route('/excluir_convivente/<int:id>')
def excluir_convivente(id):
    conn = get_db()
    conn.execute('DELETE FROM conviventes WHERE id =?', (id,))
    conn.commit()
    conn.close()
    flash('Convivente excluído!')
    return redirect(url_for('conviventes'))

@app.route('/chamada')
def chamada():
    conn = get_db()
    conviventes = conn.execute('SELECT * FROM conviventes ORDER BY quarto, leito').fetchall()
    conn.close()
    return render_template('chamada.html', conviventes=conviventes)

@app.route('/salvar_chamada', methods=['POST'])
def salvar_chamada():
    periodo = request.form['periodo']
    data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO chamadas (data, periodo) VALUES (?,?)', (data, periodo))
    chamada_id = cur.lastrowid

    for key, value in request.form.items():
        if key.startswith('presente_'):
            convivente_id = key.split('_')[1]
            presente = 1 if value == 'on' else 0
            cur.execute('INSERT INTO presencas (chamada_id, convivente_id, presente) VALUES (?,?,?)',
                       (chamada_id, convivente_id, presente))

    conn.commit()
    conn.close()
    flash('Chamada salva com sucesso!')
    return redirect(url_for('index'))

@app.route('/relatorios')
def relatorios():
    return render_template('relatorios.html')

@app.route('/relatorio_chamada')
def relatorio_chamada():
    conn = get_db()
    chamadas = conn.execute('SELECT * FROM chamadas ORDER BY data DESC').fetchall()
    conn.close()
    return render_template('relatorio_chamada.html', chamadas=chamadas)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
