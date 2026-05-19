from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'lar-ditoso-2024')

def get_db_connection():
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Tabela de Quartos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS quartos (
            id SERIAL PRIMARY KEY,
            numero INTEGER UNIQUE NOT NULL,
            nome VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tabela de Leitos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS leitos (
            id SERIAL PRIMARY KEY,
            quarto_id INTEGER REFERENCES quartos(id) ON DELETE CASCADE,
            numero_leito VARCHAR(10) NOT NULL,
            ocupado BOOLEAN DEFAULT FALSE,
            UNIQUE(quarto_id, numero_leito)
        )
    ''')
    # Tabela de Conviventes
    cur.execute('''
        CREATE TABLE IF NOT EXISTS conviventes (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL,
            data_nascimento DATE,
            foto_base64 TEXT,
            leito_id INTEGER REFERENCES leitos(id),
            data_entrada DATE DEFAULT CURRENT_DATE,
            data_saida DATE,
            ativo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tabela de Chamadas
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chamadas (
            id SERIAL PRIMARY KEY,
            convivente_id INTEGER REFERENCES conviventes(id),
            data_chamada DATE NOT NULL,
            presente BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(convivente_id, data_chamada)
        )
    ''')
    
    # Cria os 17 quartos iniciais se não existirem
    for i in range(1, 18):
        cur.execute('INSERT INTO quartos (numero, nome) VALUES (%s, %s) ON CONFLICT (numero) DO NOTHING', (i, f'Quarto {i}'))
    
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def index():
    init_db()
    return render_template('index.html')

# GESTÃO DE QUARTOS
@app.route('/quartos')
def lista_quartos():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT q.id, q.numero, q.nome, 
                   COUNT(l.id) as total_leitos,
                   SUM(CASE WHEN l.ocupado = TRUE THEN 1 ELSE 0 END) as leitos_ocupados
            FROM quartos q 
            LEFT JOIN leitos l ON q.id = l.quarto_id 
            GROUP BY q.id, q.numero, q.nome 
            ORDER BY q.numero
        ''')
        quartos = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('quartos.html', quartos=quartos)
    except Exception as e:
        flash(f'Erro ao carregar quartos: {str(e)}')
        return render_template('quartos.html', quartos=[])

@app.route('/quarto/<int:quarto_id>/leitos')
def lista_leitos(quarto_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM quartos WHERE id = %s', (quarto_id,))
        quarto = cur.fetchone()
        cur.execute('''
            SELECT l.*, c.nome as convivente_nome 
            FROM leitos l 
            LEFT JOIN conviventes c ON l.id = c.leito_id AND c.ativo = TRUE
            WHERE l.quarto_id = %s 
            ORDER BY l.numero_leito
        ''', (quarto_id,))
        leitos = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('leitos.html', quarto=quarto, leitos=leitos)
    except Exception as e:
        flash(f'Erro: {str(e)}')
        return redirect(url_for('lista_quartos'))

@app.route('/quarto/<int:quarto_id>/adicionar_leito', methods=['POST'])
def adicionar_leito(quarto_id):
    numero_leito = request.form['numero_leito']
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO leitos (quarto_id, numero_leito) VALUES (%s, %s)', (quarto_id, numero_leito))
        conn.commit()
        flash(f'Leito {numero_leito} adicionado com sucesso!')
    except psycopg2.IntegrityError:
        flash('Erro: Leito já existe neste quarto!')
        conn.rollback()
    except Exception as e:
        flash(f'Erro: {str(e)}')
        conn.rollback()
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('lista_leitos', quarto_id=quarto_id))

@app.route('/adicionar_quarto', methods=['POST'])
def adicionar_quarto():
    numero = request.form['numero']
    nome = request.form.get('nome', f'Quarto {numero}')
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO quartos (numero, nome) VALUES (%s, %s)', (numero, nome))
        conn.commit()
        flash(f'Quarto {numero} criado com sucesso!')
    except psycopg2.IntegrityError:
        flash('Erro: Quarto já existe!')
        conn.rollback()
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('lista_quartos'))

# GESTÃO DE CONVIVENTES - AQUI TAVA O ERRO 500
@app.route('/conviventes')
def lista_conviventes():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT c.*, 
                   COALESCE(q.numero, 0) as quarto_numero, 
                   COALESCE(l.numero_leito, 'Sem leito') as numero_leito 
            FROM conviventes c 
            LEFT JOIN leitos l ON c.leito_id = l.id 
            LEFT JOIN quartos q ON l.quarto_id = q.id 
            WHERE c.ativo = TRUE 
            ORDER BY q.numero, l.numero_leito
        ''')
        conviventes = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('conviventes.html', conviventes=conviventes)
    except Exception as e:
        flash(f'Erro ao carregar conviventes: {str(e)}')
        return render_template('conviventes.html', conviventes=[])

@app.route('/cadastrar_convivente', methods=['GET', 'POST'])
def cadastrar_convivente():
    if request.method == 'POST':
        nome = request.form['nome']
        data_nascimento = request.form['data_nascimento'] or None
        foto_base64 = request.form.get('foto_base64', '')
        leito_id = request.form['leito_id']
        
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('''
                INSERT INTO conviventes (nome, data_nascimento, foto_base64, leito_id) 
                VALUES (%s, %s, %s, %s)
            ''', (nome, data_nascimento, foto_base64, leito_id))
            cur.execute('UPDATE leitos SET ocupado = TRUE WHERE id = %s', (leito_id,))
            conn.commit()
            flash('Convivente cadastrado com sucesso!')
        except Exception as e:
            flash(f'Erro ao cadastrar: {str(e)}')
            conn.rollback()
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('lista_conviventes'))
    
    # GET: Buscar quartos e leitos vagos
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT q.id, q.numero, q.nome 
        FROM quartos q 
        WHERE EXISTS (SELECT 1 FROM leitos l WHERE l.quarto_id = q.id AND l.ocupado = FALSE)
        ORDER BY q.numero
    ''')
    quartos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('form_convivente.html', quartos=quartos)

@app.route('/api/leitos_vagos/<int:quarto_id>')
def leitos_vagos(quarto_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, numero_leito FROM leitos WHERE quarto_id = %s AND ocupado = FALSE ORDER BY numero_leito', (quarto_id,))
    leitos = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(leitos)

@app.route('/desocupar/<int:convivente_id>')
def desocupar_leito(convivente_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT leito_id FROM conviventes WHERE id = %s', (convivente_id,))
        result = cur.fetchone()
        if result and result['leito_id']:
            leito_id = result['leito_id']
            cur.execute('UPDATE conviventes SET ativo = FALSE, data_saida = CURRENT_DATE WHERE id = %s', (convivente_id,))
            cur.execute('UPDATE leitos SET ocupado = FALSE WHERE id = %s', (leito_id,))
            conn.commit()
            flash('Convivente desocupado e leito liberado!')
        else:
            flash('Convivente não encontrado ou sem leito.')
    except Exception as e:
        flash(f'Erro: {str(e)}')
        conn.rollback()
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('lista_conviventes'))

# CHAMADA
@app.route('/chamada')
def chamada():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT c.*, q.numero as quarto_numero, l.numero_leito 
            FROM conviventes c 
            LEFT JOIN leitos l ON c.leito_id = l.id 
            LEFT JOIN quartos q ON l.quarto_id = q.id 
            WHERE c.ativo = TRUE 
            ORDER BY q.numero, l.numero_leito
        ''')
        conviventes = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('chamada.html', conviventes=conviventes, data_hoje=datetime.now().strftime('%Y-%m-%d'))
    except Exception as e:
        flash(f'Erro: {str(e)}')
        return render_template('chamada.html', conviventes=[], data_hoje=datetime.now().strftime('%Y-%m-%d'))

if __name__ == '__main__':
    app.run(debug=True)
