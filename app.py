from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import calendar
import os
import base64
import pytz

app = Flask(__name__)
app.secret_key = 'sisa_2026'

# ===== CONFIG NEON POSTGRES =====
DATABASE_URL = os.environ.get('DATABASE_URL')
TABELA_CONVIVENTE = 'convivente'
TABELA_CHAMADA = 'chamada'
COLUNA_DATA_CHAMADA = 'data_chamada'
TZ = pytz.timezone('America/Sao_Paulo')
# ================================

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABELA_CONVIVENTE} (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            quarto TEXT,
            leito TEXT,
            foto TEXT,
            status TEXT DEFAULT 'Ativo'
        )
    ''')
    cur.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABELA_CHAMADA} (
            id SERIAL PRIMARY KEY,
            convivente_id INTEGER REFERENCES {TABELA_CONVIVENTE}(id),
            {COLUNA_DATA_CHAMADA} DATE NOT NULL,
            status TEXT,
            hora_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def index():
    init_db() # Cria tabelas se não existirem
    return render_template('index.html')

# ========== CADASTRO DE CONVIVENTES COM FOTO BASE64 ==========
@app.route('/conviventes')
def conviventes():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {TABELA_CONVIVENTE} ORDER BY CAST(NULLIF(quarto,'') AS INTEGER), leito")
    conviventes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('conviventes.html', conviventes=conviventes)

@app.route('/convivente/novo', methods=['GET', 'POST'])
def novo_convivente():
    if request.method == 'POST':
        nome = request.form['nome']
        quarto = request.form['quarto']
        leito = request.form['leito']
        status = request.form['status']
        foto_base64 = None

        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename!= '':
                foto_bytes = file.read()
                foto_base64 = base64.b64encode(foto_bytes).decode('utf-8')
                foto_base64 = f"data:{file.content_type};base64,{foto_base64}"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"INSERT INTO {TABELA_CONVIVENTE} (nome, quarto, leito, foto, status) VALUES (%s,%s,%s,%s,%s)", 
                    (nome, quarto, leito, foto_base64, status))
        conn.commit()
        cur.close()
        conn.close()
        flash('Convivente cadastrado com sucesso!')
        return redirect(url_for('conviventes'))

    return render_template('form_convivente.html', convivente=None, titulo="Novo Convivente")

@app.route('/convivente/editar/<int:id>', methods=['GET', 'POST'])
def editar_convivente(id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        nome = request.form['nome']
        quarto = request.form['quarto']
        leito = request.form['leito']
        status = request.form['status']
        
        cur.execute(f"SELECT foto FROM {TABELA_CONVIVENTE} WHERE id=%s", (id,))
        foto_atual = cur.fetchone()['foto']
        foto_base64 = foto_atual

        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename!= '':
                foto_bytes = file.read()
                foto_base64 = base64.b64encode(foto_bytes).decode('utf-8')
                foto_base64 = f"data:{file.content_type};base64,{foto_base64}"

        cur.execute(f"UPDATE {TABELA_CONVIVENTE} SET nome=%s, quarto=%s, leito=%s, foto=%s, status=%s WHERE id=%s", 
                    (nome, quarto, leito, foto_base64, status, id))
        conn.commit()
        cur.close()
        conn.close()
        flash('Convivente atualizado com sucesso!')
        return redirect(url_for('conviventes'))

    cur.execute(f"SELECT * FROM {TABELA_CONVIVENTE} WHERE id=%s", (id,))
    convivente = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('form_convivente.html', convivente=convivente, titulo="Editar Convivente")

@app.route('/convivente/excluir/<int:id>')
def excluir_convivente(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {TABELA_CONVIVENTE} WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Convivente excluído!')
    return redirect(url_for('conviventes'))

# ========== CHAMADA COM HORA CERTA DE SP ==========
@app.route('/salvar_chamada', methods=['POST'])
def salvar_chamada():
    dados = request.get_json()
    data = dados.get('data')
    presencas = dados.get('presencas', {})
    hora_sp = datetime.now(TZ)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {TABELA_CHAMADA} WHERE {COLUNA_DATA_CHAMADA} = %s", (data,))

    for conv_id, status in presencas.items():
        if status:
            cur.execute(f"INSERT INTO {TABELA_CHAMADA} (convivente_id, {COLUNA_DATA_CHAMADA}, status, hora_registro) VALUES (%s,%s,%s,%s)", 
                        (conv_id, data, status, hora_sp))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'ok'})

# RESTO DAS ROTAS: carometro, chamada, relatorio... troca sqlite3 por psycopg2 igual fiz acima
# Se quiser te mando o arquivo completo, mas o importante é esse esquema acima

if __name__ == '__main__':
    app.run(debug=True)
