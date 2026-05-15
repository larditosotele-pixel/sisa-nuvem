from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from datetime import datetime
import calendar
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sisa_2026'
# ===== CONFIG TRAVADA - 14/05/2026 - BANCO REAL =====
DB_NAME = 'lar_ditoso.db'
TABELA_CONVIVENTE = 'convivente'
TABELA_CHAMADA = 'chamada'
COLUNA_DATA_CHAMADA = 'data_chamada'
UPLOAD_FOLDER = 'static/fotos_conviventes'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# ====================================================

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

# ========== CAROMETRO ==========
@app.route('/carometro')
def carometro():
    ordem = request.args.get('sort', 'quarto')
    conn = get_db_connection()
    cursor = conn.cursor()
    if ordem == 'nome':
        cursor.execute(f"SELECT * FROM {TABELA_CONVIVENTE} ORDER BY nome")
    else:
        cursor.execute(f"SELECT * FROM {TABELA_CONVIVENTE} ORDER BY CAST(quarto AS INTEGER), CAST(leito AS TEXT)")
    conviventes = cursor.fetchall()
    conn.close()
    return render_template('carometro.html', conviventes=conviventes, ordem=ordem, orientacao='retrato')

@app.route('/carometro-paisagem')
def carometro_paisagem():
    ordem = request.args.get('sort', 'quarto')
    conn = get_db_connection()
    cursor = conn.cursor()
    if ordem == 'nome':
        cursor.execute(f"SELECT * FROM {TABELA_CONVIVENTE} ORDER BY nome")
    else:
        cursor.execute(f"SELECT * FROM {TABELA_CONVIVENTE} ORDER BY CAST(quarto AS INTEGER), CAST(leito AS TEXT)")
    conviventes = cursor.fetchall()
    conn.close()
    return render_template('carometro.html', conviventes=conviventes, ordem=ordem, orientacao='paisagem')

# ========== CHAMADA ==========
@app.route('/chamada')
def chamada():
    data_param = request.args.get('data')
    hoje = data_param if data_param else datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABELA_CONVIVENTE} ORDER BY nome")
    conviventes = cursor.fetchall()

    cursor.execute(f"SELECT convivente_id, status FROM {TABELA_CHAMADA} WHERE {COLUNA_DATA_CHAMADA} =?", (hoje,))
    chamadas_salvas = {row['convivente_id']: row['status'] for row in cursor.fetchall()}

    conn.close()
    return render_template('chamada.html', conviventes=conviventes, hoje=hoje, chamadas_salvas=chamadas_salvas)

@app.route('/salvar_chamada', methods=['POST'])
def salvar_chamada():
    dados = request.get_json()
    data = dados.get('data')
    presencas = dados.get('presencas', {})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {TABELA_CHAMADA} WHERE {COLUNA_DATA_CHAMADA} =?", (data,))

    for conv_id, status in presencas.items():
        if status:
            cursor.execute(f"INSERT INTO {TABELA_CHAMADA} (convivente_id, {COLUNA_DATA_CHAMADA}, status) VALUES (?,?,?)", (conv_id, data, status))

    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# ===== ROTAS NOVAS PRO MENU FUNCIONAR =====
@app.route('/gerenciar_conviventes')
def gerenciar_conviventes():
    return redirect(url_for('conviventes'))

@app.route('/relatorio')
def relatorio():
    return redirect(url_for('relatorio_chamada'))
# ==========================================

@app.route('/relatorio_chamada')
def relatorio_chamada():
    conn = get_db_connection()
    cursor = conn.cursor()
    hoje = datetime.now()
    ano = hoje.year
    mes = hoje.month
    meses = ['', 'JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO',
            'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']
    nome_mes = meses[mes]
    num_dias = calendar.monthrange(ano, mes)[1]
    dias_mes = list(range(1, num_dias + 1))
    dias_semana = [datetime(ano, mes, dia).weekday() for dia in dias_mes]
    cursor.execute(f"SELECT * FROM {TABELA_CONVIVENTE} ORDER BY nome")
    conviventes = cursor.fetchall()
    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{num_dias}"

    cursor.execute(f"""
        SELECT convivente_id, strftime('%d', {COLUNA_DATA_CHAMADA}) as dia, status
        FROM {TABELA_CHAMADA}
        WHERE {COLUNA_DATA_CHAMADA} BETWEEN? AND?
    """, (data_inicio, data_fim))
    chamadas = {}
    for row in cursor.fetchall():
        conv_id = row['convivente_id']
        dia = int(row['dia'])
        if conv_id not in chamadas:
            chamadas[conv_id] = {}
        chamadas[conv_id][dia] = row['status']
    conn.close()

    hoje_formatado = datetime.now().strftime('%d/%m/%Y')

    return render_template('relatorio_chamada.html',
                           conviventes=conviventes,
                           chamadas=chamadas,
                           dias_mes=dias_mes,
                           dias_semana=dias_semana,
                           nome_mes=nome_mes,
                           ano=ano,
                           hoje=hoje_formatado)

@app.route('/relatorio_chamada_branco')
def relatorio_chamada_branco():
    mes = datetime.now().month
    ano = datetime.now().year
    hoje = datetime.now().strftime('%d/%m/%Y')

    dias_mes = list(range(1, calendar.monthrange(ano, mes)[1] + 1))
    dias_semana = [calendar.weekday(ano, mes, dia) for dia in dias_mes]
    nome_mes = calendar.month_name[mes].capitalize()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABELA_CONVIVENTE} ORDER BY CAST(quarto AS INTEGER), CAST(leito AS TEXT)")
    conviventes = cursor.fetchall()
    conn.close()

    return render_template(
        'relatorio_chamada_em_branco.html',
        conviventes=conviventes,
        dias_mes=dias_mes,
        dias_semana=dias_semana,
        nome_mes=nome_mes,
        ano=ano,
        hoje=hoje
    )

# ========== CADASTRO DE CONVIVENTES COM FOTO ==========
@app.route('/conviventes')
def conviventes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABELA_CONVIVENTE} ORDER BY CAST(quarto AS INTEGER), CAST(leito AS TEXT)")
    conviventes = cursor.fetchall()
    conn.close()
    return render_template('conviventes.html', conviventes=conviventes)

@app.route('/convivente/novo', methods=['GET', 'POST'])
def novo_convivente():
    if request.method == 'POST':
        nome = request.form['nome']
        quarto = request.form['quarto']
        leito = request.form['leito']
        foto_path = None

        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename!= '' and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                foto_path = f'fotos_conviventes/{filename}'

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO {TABELA_CONVIVENTE} (nome, quarto, leito, foto) VALUES (?,?,?,?)", (nome, quarto, leito, foto_path))
        conn.commit()
        conn.close()
        flash('Convivente cadastrado com sucesso!')
        return redirect(url_for('conviventes'))

    return render_template('form_convivente.html', convivente=None, titulo="Novo Convivente")

@app.route('/convivente/editar/<int:id>', methods=['GET', 'POST'])
def editar_convivente(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        nome = request.form['nome']
        quarto = request.form['quarto']
        leito = request.form['leito']

        cursor.execute(f"SELECT foto FROM {TABELA_CONVIVENTE} WHERE id=?", (id,))
        foto_atual = cursor.fetchone()['foto']
        foto_path = foto_atual

        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename!= '' and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                foto_path = f'fotos_conviventes/{filename}'
                if foto_atual and os.path.exists(os.path.join('static', foto_atual)):
                    os.remove(os.path.join('static', foto_atual))

        cursor.execute(f"UPDATE {TABELA_CONVIVENTE} SET nome=?, quarto=?, leito=?, foto=? WHERE id=?", (nome, quarto, leito, foto_path, id))
        conn.commit()
        conn.close()
        flash('Convivente atualizado com sucesso!')
        return redirect(url_for('conviventes'))

    cursor.execute(f"SELECT * FROM {TABELA_CONVIVENTE} WHERE id=?", (id,))
    convivente = cursor.fetchone()
    conn.close()
    return render_template('form_convivente.html', convivente=convivente, titulo="Editar Convivente")

@app.route('/convivente/excluir/<int:id>')
def excluir_convivente(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT foto FROM {TABELA_CONVIVENTE} WHERE id=?", (id,))
    foto = cursor.fetchone()['foto']
    if foto and os.path.exists(os.path.join('static', foto)):
        os.remove(os.path.join('static', foto))

    cursor.execute(f"DELETE FROM {TABELA_CONVIVENTE} WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Convivente excluído!')
    return redirect(url_for('conviventes'))

@app.route('/logout')
def logout():
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
