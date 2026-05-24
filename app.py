from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
import psycopg2.extras
import os
from datetime import datetime, date
import base64

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sisa_sistema_2024')

def get_db_connection():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/conviventes')
def conviventes():
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

# COLE SUAS OUTRAS ROTAS AQUI SE TIVER
# Ex: /relatorios, /enfermagem, /farmacia, etc
# Só não precisa mais colocar @login_required em nenhuma

if __name__ == '__main__':
    app.run(debug=True)
