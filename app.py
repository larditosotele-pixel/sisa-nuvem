from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = os.urandom(24)

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não configurada!")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS conviventes (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            data_nascimento DATE,
            quarto TEXT,
            leito TEXT,
            foto_base64 TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chamadas (
            id SERIAL PRIMARY KEY,
            data_chamada DATE NOT NULL,
            presentes TEXT,
            ausentes TEXT,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/conviventes')
def lista_conviventes(): # <- NOME CERTO PRO INDEX.HTML
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM conviventes ORDER BY nome')
    conviventes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('conviventes.html', conviventes=conviventes)

@app.route('/cadastrar_convivente', methods=['GET', 'POST'])
def cadastrar_convivente():
    if request.method == 'POST':
        nome = request.form['nome']
        data_nascimento = request.form['data_nascimento']
        quarto = request.form['quarto']
        leito = request.form['leito']
        foto_base64 = request.form.get('foto_base64', '')
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO conviventes (nome, data_nascimento, quarto, leito, foto_base64) VALUES (%s, %s, %s, %s, %s)',
                    (nome, data_nascimento, quarto, leito, foto_base64))
        conn.commit()
        cur.close()
        conn.close()
        flash('Convivente cadastrado com sucesso!')
        return redirect(url_for('lista_conviventes'))
    
    return render_template('form_convivente.html')

@app.route('/chamada')
def chamada(): # <- NOME CERTO PRO INDEX.HTML
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM conviventes ORDER BY nome')
    conviventes = cur.fetchall()
    cur.close()
    conn.close()
    fuso_sp = pytz.timezone('America/Sao_Paulo')
    data_hoje = datetime.now(fuso_sp).strftime('%Y-%m-%d')
    return render_template('chamada.html', conviventes=conviventes, data_hoje=data_hoje)

@app.route('/salvar_chamada', methods=['POST'])
def salvar_chamada():
    data_chamada = request.form['data_chamada']
    presentes = request.form.getlist('presentes')
    ausentes = request.form.getlist('ausentes')
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO chamadas (data_chamada, presentes, ausentes) VALUES (%s, %s, %s)',
                (data_chamada, ','.join(presentes), ','.join(ausentes)))
    conn.commit()
    cur.close()
    conn.close()
    flash('Chamada salva com sucesso!')
    return redirect(url_for('index'))

# Roda init_db uma vez quando o app sobe
with app.app_context():
    try:
        init_db()
        print("Tabelas criadas/verificadas!")
    except Exception as e:
        print(f"Erro no init_db: {e}")

if __name__ == '__main__':
    app.run(debug=True)
