from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import psycopg2
import psycopg2.extras
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import base64

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sisa_sistema_2024')

def get_db_connection():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    return conn

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['senha'], senha):
            session['user_id'] = user['id']
            session['usuario'] = user['usuario']
            session['nome'] = user['nome']
            session['nivel'] = user['nivel']
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/conviventes')
def conviventes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT c.*, q.numero as quarto, l.numero as leito 
        FROM conviventes c
        LEFT JOIN leitos l ON c.leito_id = l.id
        LEFT JOIN quartos q ON l.quarto_id = q.id
        ORDER BY c.nome
    """)
    conviventes = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('conviventes.html', conviventes=conviventes)

@app.route('/carometro')
def carometro():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    ordem = request.args.get('ordem', 'alfabetica')
    conn = None
    cur = None
    
    def buscar_conviventes(cursor, ordem_param):
        if ordem_param == 'quarto':
            cursor.execute("""
                SELECT c.id, c.nome, c.foto_base64, q.numero as quarto, l.numero as leito 
                FROM conviventes c
                JOIN leitos l ON c.leito_id = l.id
                JOIN quartos q ON l.quarto_id = q.id
                ORDER BY q.numero, l.numero
            """)
        else:
            cursor.execute("""
                SELECT c.id, c.nome, c.foto_base64, q.numero as quarto, l.numero as leito 
                FROM conviventes c
                JOIN leitos l ON c.leito_id = l.id
                JOIN quartos q ON l.quarto_id = q.id
                ORDER BY c.nome ASC
            """)
        return cursor.fetchall()

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        conviventes = buscar_conviventes(cur, ordem)
        
    except psycopg2.OperationalError:
        if conn: conn.close()
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        conviventes = buscar_conviventes(cur, ordem)
        
    except Exception as e:
        print(f"Erro no carometro: {e}")
        return "Erro ao carregar carômetro. Tente novamente.", 500
        
    finally:
        if cur: cur.close()
        if conn: conn.close()
        
    return render_template('carometro.html', conviventes=conviventes)

# MANTÉM TODAS AS OUTRAS ROTAS QUE VOCÊ JÁ TEM ABAIXO
# Ex: /relatorios, /enfermagem, /farmacia, etc...

if __name__ == '__main__':
    app.run(debug=True)
