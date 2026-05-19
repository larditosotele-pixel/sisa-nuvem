from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'lar-ditoso-2024')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 # 5MB limite - CORRIGIDO

def get_db_connection():
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS quartos (
            id SERIAL PRIMARY KEY,
            numero INTEGER UNIQUE NOT NULL,
            nome VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS leitos (
            id SERIAL PRIMARY KEY,
            quarto_id INTEGER REFERENCES quartos(id) ON DELETE CASCADE,
            numero_leito VARCHAR(10) NOT NULL,
            ocupado BOOLEAN DEFAULT FALSE,
            UNIQUE(quarto_id, numero_leito)
        )
    ''')
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
    for i in range(1, 18):
        cur.execute('INSERT INTO quartos (numero, nome) VALUES (%s, %s) ON CONFLICT (numero) DO NOTHING', (i, f'Quarto {i}'))
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def index():
    init_db()
    return redirect(url_for('mapa_leitos'))

@app.route('/mapa_leitos')
def mapa_leitos():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT q.id as quarto_id, q.numero as quarto_numero,
                   l.id as leito_id, l.numero_leito, l.ocupado,
                   c.id as convivente_id, c.nome as convivente_nome, c.foto_base64, c.data_nascimento
            FROM quartos q
            LEFT JOIN leitos l ON q.id = l.quarto_id
            LEFT JOIN conviventes c ON l.id = c.leito_id AND c.ativo = TRUE
            ORDER BY q.numero, 
                     CASE WHEN l.numero_leito ~ '^[0-9]+$' 
                          THEN CAST(l.numero_leito AS INTEGER) 
                          ELSE 999 END,
                     l.numero_leito
        ''')
        dados = cur.fetchall()

        quartos = {}
        for row in dados:
            q_num = row['quarto_numero']
            if q_num not in quartos:
                quartos[q_num] = {'id': row['quarto_id'], 'numero': q_num, 'leitos': []}
            if row['leito_id']:
                quartos[q_num]['leitos'].append(row)

        cur.close()
        conn.close()
        return render_template('mapa_leitos.html', quartos=quartos.values())
    except Exception as e:
        flash(f'Erro ao carregar mapa: {str(e)}')
        return render_template('mapa_leitos.html', quartos=[])

@app.route('/quarto/<int:quarto_id>/adicionar_leito_mapa', methods=['POST'])
def adicionar_leito_mapa(quarto_id):
    quarto_numero_redirect = None
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT numero FROM quartos WHERE id = %s', (quarto_id,))
        result = cur.fetchone()
        if result:
            quarto_numero_redirect = result['numero']

        cur.execute('SELECT numero_leito FROM leitos WHERE quarto_id = %s', (quarto_id,))
        leitos_existentes = [int(row['numero_leito']) for row in cur.fetchall() if row['numero_leito'].isdigit()]
        proximo_numero = 1
        while proximo_numero in leitos_existentes:
            proximo_numero += 1
        cur.execute('INSERT INTO leitos (quarto_id, numero_leito) VALUES (%s, %s)', (quarto_id, str(proximo_numero)))
        conn.commit()
        flash(f'Leito {proximo_numero} adicionado!')
    except Exception as e:
        flash(f'Erro: {str(e)}')
        conn.rollback()
    finally:
        cur.close()
        conn.close()

    if quarto_numero_redirect:
        return redirect(url_for('mapa_leitos') + f'#quarto-{quarto_numero_redirect}')
    return redirect(url_for('mapa_leitos'))

@app.route('/adicionar_quarto_mapa', methods=['POST'])
def adicionar_quarto_mapa():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT numero FROM quartos')
        quartos_existentes = [row['numero'] for row in cur.fetchall()]
        proximo_numero = 1
        while proximo_numero in quartos_existentes:
            proximo_numero += 1
        cur.execute('INSERT INTO quartos (numero, nome) VALUES (%s, %s)', (proximo_numero, f'Quarto {proximo_numero}'))
        conn.commit()
        flash(f'Quarto {proximo_numero} criado!')
    except Exception as e:
        flash(f'Erro: {str(e)}')
        conn.rollback()
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('mapa_leitos'))

@app.route('/cadastrar_convivente', methods=['GET', 'POST'])
def cadastrar_convivente():
    leito_id_pre = request.args.get('leito_id', type=int)
    quarto_numero_redirect = None

    if request.method == 'POST':
        nome = request.form['nome']
        data_nascimento = request.form['data_nascimento'] or None
        foto_base64 = request.form.get('foto_base64', '')
        leito_id = request.form['leito_id']

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('SELECT q.numero FROM leitos l JOIN quartos q ON l.quarto_id = q.id WHERE l.id = %s', (leito_id,))
            result = cur.fetchone()
            if result:
                quarto_numero_redirect = result['numero']

            cur.execute('SELECT id FROM conviventes WHERE leito_id = %s AND ativo = TRUE', (leito_id,))
            if cur.fetchone():
                flash('Erro: Este leito já está ocupado!')
                conn.rollback()
            else:
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

        if quarto_numero_redirect:
            return redirect(url_for('mapa_leitos') + f'#quarto-{quarto_numero_redirect}')
        return redirect(url_for('mapa_leitos'))

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT DISTINCT q.id, q.numero
            FROM quartos q
            WHERE EXISTS (SELECT 1 FROM leitos l WHERE l.quarto_id = q.id AND l.ocupado = FALSE)
            ORDER BY q.numero
        ''')
        quartos = cur.fetchall()

        leito_pre_selecionado = None
        quarto_pre_selecionado = None
        if leito_id_pre:
            cur.execute('''
                SELECT l.id, l.numero_leito, l.quarto_id, q.numero as quarto_numero
                FROM leitos l
                JOIN quartos q ON l.quarto_id = q.id
                WHERE l.id = %s AND l.ocupado = FALSE
            ''', (leito_id_pre,))
            leito_pre_selecionado = cur.fetchone()
            if leito_pre_selecionado:
                quarto_pre_selecionado = leito_pre_selecionado['quarto_id']

    except Exception as e:
        flash(f'Erro ao carregar formulário: {str(e)}')
        quartos = []
        leito_pre_selecionado = None
        quarto_pre_selecionado = None
    finally:
        cur.close()
        conn.close()

    return render_template('form_convivente.html',
                           quartos=quartos,
                           leito_pre_selecionado=leito_pre_selecionado,
                           quarto_pre_selecionado=quarto_pre_selecionado)

@app.route('/editar_convivente/<int:convivente_id>', methods=['POST'])
def editar_convivente(convivente_id):
    acao = request.form.get('acao')
    quarto_numero_redirect = None
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT q.numero FROM conviventes c
            JOIN leitos l ON c.leito_id = l.id
            JOIN quartos q ON l.quarto_id = q.id
            WHERE c.id = %s
        ''', (convivente_id,))
        result = cur.fetchone()
        if result:
            quarto_numero_redirect = result['numero']

        if acao == 'salvar':
            nome = request.form['nome']
            data_nascimento = request.form['data_nascimento'] or None
            foto_base64 = request.form.get('foto_base64')

            if foto_base64:
                cur.execute('UPDATE conviventes SET nome = %s, data_nascimento = %s, foto_base64 = %s WHERE id = %s',
                           (nome, data_nascimento, foto_base64, convivente_id))
            else:
                cur.execute('UPDATE conviventes SET nome = %s, data_nascimento = %s WHERE id = %s',
                           (nome, data_nascimento, convivente_id))
            flash('Dados do convivente atualizados!')

        elif acao == 'desocupar':
            cur.execute('SELECT leito_id FROM conviventes WHERE id = %s', (convivente_id,))
            result = cur.fetchone()
            if result and result['leito_id']:
                leito_id = result['leito_id']
                cur.execute('UPDATE conviventes SET ativo = FALSE, data_saida = CURRENT_DATE WHERE id = %s', (convivente_id,))
                cur.execute('UPDATE leitos SET ocupado = FALSE WHERE id = %s', (leito_id,))
                flash('Leito desocupado com sucesso!')

        conn.commit()
    except Exception as e:
        flash(f'Erro: {str(e)}')
        conn.rollback()
    finally:
        cur.close()
        conn.close()

    if quarto_numero_redirect:
        return redirect(url_for('mapa_leitos') + f'#quarto-{quarto_numero_redirect}')
    return redirect(url_for('mapa_leitos'))

@app.route('/api/leitos_vagos/<int:quarto_id>')
def leitos_vagos(quarto_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, numero_leito FROM leitos 
        WHERE quarto_id = %s AND ocupado = FALSE 
        ORDER BY CASE WHEN numero_leito ~ '^[0-9]+$' 
                      THEN CAST(numero_leito AS INTEGER) 
                      ELSE 999 END,
                 numero_leito
    ''', (quarto_id,))
    leitos = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(leitos)

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
            ORDER BY q.numero, 
                     CASE WHEN l.numero_leito ~ '^[0-9]+$' 
                          THEN CAST(l.numero_leito AS INTEGER) 
                          ELSE 999 END,
                     l.numero_leito
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
