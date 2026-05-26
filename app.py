import pytz
from datetime import datetime, timedelta
import os
import psycopg2
import psycopg2.extras
import base64
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'uma_chave_secreta_muito_segura_e_dificil')

# FUSO HORÁRIO DE SÃO PAULO - CORRIGE O BUG DAS 21H
fuso_sp = pytz.timezone('America/Sao_Paulo')

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL não definida")
    conn = psycopg2.connect(db_url)
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mapa_leitos')
def mapa_leitos():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM quartos ORDER BY numero')
    quartos_db = cur.fetchall()
    quartos = []
    for quarto in quartos_db:
        cur.execute('''
            SELECT
                l.id as leito_id, l.numero_leito,
                c.id as convivente_id, c.nome as convivente_nome,
                c.foto_base64
            FROM leitos l
            LEFT JOIN conviventes c ON l.id = c.leito_id AND c.ativo = TRUE
            WHERE l.quarto_id = %s
            ORDER BY
                CASE WHEN l.numero_leito ~ '^[0-9]+$'
                     THEN CAST(l.numero_leito AS INTEGER)
                     ELSE 999 END
        ''', (quarto['id'],))
        leitos = cur.fetchall()
        leitos_data = []
        for leito in leitos:
            leitos_data.append({
                'leito_id': leito['leito_id'],
                'numero_leito': leito['numero_leito'],
                'ocupado': leito['convivente_id'] is not None,
                'convivente_id': leito['convivente_id'],
                'convivente_nome': leito['convivente_nome'],
                'foto_base64': leito['foto_base64']
            })
        quartos.append({'id': quarto['id'], 'numero': quarto['numero'], 'leitos': leitos_data})
    cur.close()
    conn.close()
    return render_template('mapa_leitos.html', quartos=quartos)

@app.route('/adicionar_quarto_mapa', methods=['POST'])
def adicionar_quarto_mapa():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT MAX(numero) FROM quartos')
    max_num = cur.fetchone()[0]
    novo_num = (max_num or 0) + 1
    cur.execute('INSERT INTO quartos (numero) VALUES (%s)', (novo_num,))
    conn.commit()
    cur.close()
    conn.close()
    flash(f'Quarto {novo_num} criado com sucesso!')
    return redirect(url_for('mapa_leitos') + f'#quarto-{novo_num}')

@app.route('/adicionar_leito_mapa/<int:quarto_id>', methods=['POST'])
def adicionar_leito_mapa(quarto_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT MAX(CAST(numero_leito AS INTEGER)) FROM leitos WHERE quarto_id = %s AND numero_leito ~ \'^[0-9]+$\'', (quarto_id,))
    max_num = cur.fetchone()[0]
    novo_num = (max_num or 0) + 1
    cur.execute('INSERT INTO leitos (quarto_id, numero_leito) VALUES (%s, %s)', (quarto_id, str(novo_num)))
    conn.commit()
    cur.execute('SELECT numero FROM quartos WHERE id = %s', (quarto_id,))
    quarto_num = cur.fetchone()[0]
    cur.close()
    conn.close()
    flash(f'Leito {novo_num} adicionado ao Quarto {quarto_num}!')
    return redirect(url_for('mapa_leitos') + f'#quarto-{quarto_num}')

@app.route('/chamada', methods=['GET', 'POST'])
def chamada():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        # PEGA A DATA DO FORMULÁRIO
        data_str = request.form.get('data_chamada')
        hoje = datetime.strptime(data_str, '%Y-%m-%d').date()

        # PRIMEIRO: APAGA TODAS AS CHAMADAS DESSE DIA - CORRIGE O BUG DE DESMARCAR
        cur.execute('DELETE FROM chamadas WHERE data_chamada = %s', (hoje,))

        # SEGUNDO: INSERE SÓ QUEM TEM STATUS MARCADO
        dados_para_salvar = []
        for key, value in request.form.items():
            if key.startswith('status_') and value: # Só salva se marcou P, F, A ou H
                convivente_id = int(key.split('_')[1])
                dados_para_salvar.append((convivente_id, hoje, value))

        if dados_para_salvar:
            args_str = ','.join(cur.mogrify("(%s,%s,%s)", i).decode('utf-8') for i in dados_para_salvar)
            cur.execute(f"""
                INSERT INTO chamadas (convivente_id, data_chamada, status)
                VALUES {args_str}
            """)

        conn.commit()
        cur.close()
        conn.close()
        flash('Chamada salva com sucesso!')
        return redirect(url_for('chamada', data=data_str))

    # PARTE DO GET - CORRIGIDA COM FUSO E NAVEGAÇÃO
    ordem = request.args.get('ordem', 'quarto')
    data_str = request.args.get('data')

    # USA FUSO DE SP PRA PEGAR DATA CORRETA
    if data_str:
        try:
            hoje = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            hoje = datetime.now(fuso_sp).date()
    else:
        hoje = datetime.now(fuso_sp).date()

    if ordem == 'alfabetica':
        order_by = 'c.nome ASC'
    else:
        order_by = '''q.numero,
                     CASE WHEN l.numero_leito ~ '^[0-9]+$'
                          THEN CAST(l.numero_leito AS INTEGER)
                          ELSE 999 END'''

    cur.execute(f'''
        SELECT
            c.id, c.nome, c.foto_base64,
            q.numero as quarto_numero, l.numero_leito,
            ch.status as status
        FROM conviventes c
        LEFT JOIN leitos l ON c.leito_id = l.id
        LEFT JOIN quartos q ON l.quarto_id = q.id
        LEFT JOIN chamadas ch ON c.id = ch.convivente_id AND ch.data_chamada = %s
        WHERE c.ativo = TRUE
        ORDER BY {order_by}
    ''', (hoje,))

    conviventes = cur.fetchall()
    cur.close()
    conn.close()

    # DATAS PRA NAVEGAÇÃO
    dia_anterior = (hoje - timedelta(days=1)).strftime('%Y-%m-%d')
    proximo_dia = (hoje + timedelta(days=1)).strftime('%Y-%m-%d')

    return render_template('chamada.html',
                         conviventes=conviventes,
                         data_hoje=hoje.strftime('%d/%m/%Y'),
                         data_selecionada=hoje.strftime('%Y-%m-%d'),
                         dia_anterior=dia_anterior,
                         proximo_dia=proximo_dia,
                         ordem=ordem)

@app.route('/cadastrar_convivente', methods=['GET', 'POST'])
def cadastrar_convivente():
    leito_id = request.args.get('leito_id', type=int)
    leito_info = None

    if leito_id:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('''
            SELECT l.id, l.numero_leito, q.numero as quarto_numero
            FROM leitos l
            JOIN quartos q ON l.quarto_id = q.id
            WHERE l.id = %s AND l.ocupado = FALSE
        ''', (leito_id,))
        leito_info = cur.fetchone()
        cur.close()
        conn.close()

    if request.method == 'POST':
        nome = request.form['nome']
        foto = request.files['foto']
        leito_id_form = leito_id or request.form.get('leito_id')

        if not leito_id_form:
            flash('Erro: Selecione um leito')
            return redirect(url_for('cadastrar_convivente'))

        if foto:
            foto_base64 = base64.b64encode(foto.read()).decode('utf-8')
            foto_base64 = f"data:image/jpeg;base64,{foto_base64}"
        else:
            foto_base64 = None

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO conviventes (nome, foto_base64, leito_id) VALUES (%s, %s, %s)',
                    (nome, foto_base64, leito_id_form))
        cur.execute('UPDATE leitos SET ocupado = TRUE WHERE id = %s', (leito_id_form,))
        conn.commit()
        cur.close()
        conn.close()
        flash(f'{nome} cadastrado com sucesso!')
        return redirect(url_for('mapa_leitos'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('''
        SELECT l.id, l.numero_leito, q.numero as quarto_numero
        FROM leitos l
        JOIN quartos q ON l.quarto_id = q.id
        WHERE l.ocupado = FALSE
        ORDER BY q.numero,
                 CASE WHEN l.numero_leito ~ '^[0-9]+$'
                      THEN CAST(l.numero_leito AS INTEGER)
                      ELSE 999 END
    ''')
    leitos_vazios = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('form_convivente.html', leitos_vazios=leitos_vazios, leito_info=leito_info)

@app.route('/editar_convivente/<int:id>', methods=['POST'])
def editar_convivente(id):
    acao = request.form['acao']
    conn = get_db_connection()
    cur = conn.cursor()
    if acao == 'salvar':
        nome = request.form['nome']
        cur.execute('UPDATE conviventes SET nome = %s WHERE id = %s', (nome, id))
        flash('Convivente atualizado!')
    elif acao == 'desocupar':
        cur.execute('SELECT leito_id FROM conviventes WHERE id = %s', (id,))
        leito_id = cur.fetchone()[0]
        cur.execute('UPDATE conviventes SET ativo = FALSE, leito_id = NULL WHERE id = %s', (id,))
        if leito_id:
            cur.execute('UPDATE leitos SET ocupado = FALSE WHERE id = %s', (leito_id,))
        flash('Leito desocupado!')
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('mapa_leitos'))

@app.route('/relatorio_mensal')
def relatorio_mensal():
    from datetime import datetime
    import calendar

    hoje = datetime.now(fuso_sp) # USA FUSO SP
    mes = request.args.get('mes', default=hoje.month, type=int)
    ano = request.args.get('ano', default=hoje.year, type=int)

    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dias_mes = list(range(1, ultimo_dia + 1))
    dias_impares = [d for d in dias_mes if d % 2!= 0]
    dias_pares = [d for d in dias_mes if d % 2 == 0]

    fins_de_semana = []
    for dia in dias_mes:
        data = datetime(ano, mes, dia)
        if data.weekday() >= 5:
            fins_de_semana.append(dia)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('''
        SELECT c.id, c.nome, q.numero as quarto_numero, l.numero_leito
        FROM conviventes c
        LEFT JOIN leitos l ON c.leito_id = l.id
        LEFT JOIN quartos q ON l.quarto_id = q.id
        WHERE c.ativo = TRUE
        ORDER BY c.nome ASC
    ''')
    conviventes = cur.fetchall()

    primeiro_dia = f'{ano}-{mes:02d}-01'
    ultimo_dia_str = f'{ano}-{mes:02d}-{ultimo_dia:02d}'
    cur.execute('''
        SELECT convivente_id, EXTRACT(DAY FROM data_chamada) as dia, status
        FROM chamadas
        WHERE data_chamada BETWEEN %s AND %s
    ''', (primeiro_dia, ultimo_dia_str))

    chamadas = {}
    for row in cur.fetchall():
        conv_id = row['convivente_id']
        dia = int(row['dia'])
        if conv_id not in chamadas:
            chamadas[conv_id] = {}
        chamadas[conv_id][dia] = row['status']

    cur.close()
    conn.close()

    meses_nomes = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    return render_template('relatorio.html',
                         conviventes=conviventes,
                         chamadas=chamadas,
                         dias_impares=dias_impares,
                         dias_pares=dias_pares,
                         fins_de_semana=fins_de_semana,
                         mes=mes,
                         ano=ano,
                         mes_nome=meses_nomes[mes])

@app.route('/relatorio_branco')
def relatorio_branco():
    from datetime import datetime
    import calendar

    hoje = datetime.now(fuso_sp) # USA FUSO SP
    mes = request.args.get('mes', default=hoje.month, type=int)
    ano = request.args.get('ano', default=hoje.year, type=int)

    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dias_mes = list(range(1, ultimo_dia + 1))
    dias_impares = [d for d in dias_mes if d % 2!= 0]
    dias_pares = [d for d in dias_mes if d % 2 == 0]

    fins_de_semana = []
    for dia in dias_mes:
        data = datetime(ano, mes, dia)
        if data.weekday() >= 5:
            fins_de_semana.append(dia)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('''
        SELECT c.id, c.nome, q.numero as quarto_numero, l.numero_leito
        FROM conviventes c
        LEFT JOIN leitos l ON c.leito_id = l.id
        LEFT JOIN quartos q ON l.quarto_id = q.id
        WHERE c.ativo = TRUE
        ORDER BY c.nome ASC
    ''')
    conviventes = cur.fetchall()
    cur.close()
    conn.close()

    meses_nomes = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    return render_template('relatorio_branco.html',
                         conviventes=conviventes,
                         dias_impares=dias_impares,
                         dias_pares=dias_pares,
                         fins_de_semana=fins_de_semana,
                         mes=mes,
                         ano=ano,
                         mes_nome=meses_nomes[mes])

@app.route('/carometro')
def carometro():
    ordem = request.args.get('ordem', 'quarto')
    orientacao = request.args.get('orientacao', 'vertical')
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        if ordem == 'alfabetica':
            cur.execute("""
                SELECT
                    c.id,
                    c.nome,
                    q.numero as quarto_numero,
                    l.numero_leito,
                    c.foto_base64
                FROM conviventes c
                LEFT JOIN leitos l ON c.leito_id = l.id
                LEFT JOIN quartos q ON l.quarto_id = q.id
                WHERE c.ativo = TRUE AND c.leito_id IS NOT NULL
                ORDER BY c.nome COLLATE "C"
            """)
        else:
            cur.execute("""
                SELECT
                    c.id,
                    c.nome,
                    q.numero as quarto_numero,
                    l.numero_leito,
                    c.foto_base64
                FROM conviventes c
                LEFT JOIN leitos l ON c.leito_id = l.id
                LEFT JOIN quartos q ON l.quarto_id = q.id
                WHERE c.ativo = TRUE AND c.leito_id IS NOT NULL
                ORDER BY
                    q.numero,
                    CASE WHEN l.numero_leito ~ '^[0-9]+$'
                         THEN CAST(l.numero_leito AS INTEGER)
                         ELSE 999 END
            """)

        conviventes = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()

        return render_template('carometro.html', conviventes=conviventes, ordem=ordem, orientacao=orientacao)

    except Exception as e:
        print(f"ERRO NO CARÔMETRO: {e}")
        return render_template('carometro.html', conviventes=[], ordem=ordem, orientacao=orientacao, erro=str(e))

if __name__ == '__main__':
    app.run(debug=True)
