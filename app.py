from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import psycopg2
import psycopg2.extras
import os
import cloudinary
import cloudinary.uploader
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sisa-lar-ditoso-2024')

# Configuração do Cloudinary
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

# Conexão com PostgreSQL do Render
def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

# Cria as tabelas se não existirem
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # EXEMPLO: Tabela de conviventes - AJUSTA PRO SEU BANCO
    cur.execute('''
        CREATE TABLE IF NOT EXISTS conviventes (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            data_nascimento DATE,
            foto_url TEXT,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # COLOCA AQUI OS CREATE TABLE DAS SUAS OUTRAS TABELAS
    
    conn.commit()
    cur.close()
    conn.close()

# Roda na primeira vez que subir
with app.app_context():
    init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM conviventes ORDER BY nome')
    conviventes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', conviventes=conviventes)

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        data_nasc = request.form['data_nascimento']
        
        foto_url = None
        if 'foto' in request.files:
            foto = request.files['foto']
            if foto.filename != '':
                upload_result = cloudinary.uploader.upload(foto)
                foto_url = upload_result['secure_url']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO conviventes (nome, data_nascimento, foto_url) VALUES (%s, %s, %s)',
                    (nome, data_nasc, foto_url))
        conn.commit()
        cur.close()
        conn.close()
        
        flash('Convivente cadastrado com sucesso!')
        return redirect(url_for('index'))
    
    return render_template('cadastrar.html')

# COLA SUAS OUTRAS ROTAS AQUI
# /editar, /excluir, /relatorio, etc...
# SÓ TROCA sqlite3 por psycopg2 e %s no lugar de ?

if __name__ == '__main__':
    app.run(debug=True)
