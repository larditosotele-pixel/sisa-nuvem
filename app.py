from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sisa_secreto_2026'

def get_db():
    conn = sqlite3.connect('sisa.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS conviventes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            quarto INTEGER NOT NULL,
            leito INTEGER NOT NULL
        )
    ''')
    # Se quiser usar foto no futuro, roda isso uma vez:
    # try:
    #     conn.execute('ALTER TABLE conviventes ADD COLUMN foto TEXT')
    # except:
    #     pass
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
    if request.method == 'POST':
        nome = request.form['nome']
        quarto = request.form['quarto']
        leito = request.form['leito']
        conn = get_db()
        conn.execute('INSERT INTO conviventes (nome, quarto, leito) VALUES (?,?,?)',
                     (nome, quarto, leito))
        conn.commit()
        conn.close()
        flash('Convivente cadastrado!')
        return redirect(url_for('conviventes'))
    return render_template('novo_convivente.html')

@app.route('/atualizar_convivente/<int:id>', methods=['GET', 'POST'])
def atualizar_convivente(id):
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

@app.route('/excluir_convivente/<int:id>')
def excluir_convivente(id):
    conn = get_db()
    conn.execute('DELETE FROM conviventes WHERE id =?', (id,))
    conn.commit()
    conn.close()
    flash('Convivente excluído!')
    return redirect(url_for('conviventes'))

@app.route('/desocupar_leito/<int:id>', methods=['POST'])
def desocupar_leito(id):
    conn = get_db()
    conn.execute('UPDATE conviventes SET nome=?, quarto=?, leito=? WHERE id=?', 
                 ('VAGO', 0, 0, id))
    conn.commit()
    conn.close()
    flash('Leito desocupado!')
    return redirect(url_for('conviventes'))

# ROTAS STUB - SÓ PRA NÃO DAR ERRO 500 NO MENU
@app.route('/chamada')
def chamada():
    return "Página de Chamada em construção"

@app.route('/relatorio_chamada')
def relatorio_chamada():
    return "Página de Relatório de Chamada em construção"

@app.route('/relatorio_chamada_branco')
def relatorio_chamada_branco():
    return "Relatório de Chamada em Branco - Em construção"

@app.route('/relatorio')
def relatorio():
    return "Página de Relatório em construção"

@app.route('/config')
def config():
    return "Página de Configurações em construção"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
