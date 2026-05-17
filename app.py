from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sisa_secreto_2026'

# Pasta pra salvar fotos
UPLOAD_FOLDER = 'static/fotos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Extensões permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = sqlite3.connect('sisa.db')
    conn.row_factory = sqlite3.Row
    return conn

# Cria tabela se não existir
def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS conviventes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            quarto INTEGER NOT NULL,
            leito INTEGER NOT NULL,
            foto TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/conviventes')
def conviventes():
    conn = get_db()
    conviventes = conn.execute('SELECT * FROM conviventes ORDER BY id').fetchall()
    conn.close()
    return render_template('conviventes.html', conviventes=conviventes)

@app.route('/novo_convivente', methods=['GET', 'POST'])
def novo_convivente():
    quarto = request.args.get('quarto', '')
    if request.method == 'POST':
        nome = request.form['nome']
        quarto = request.form['quarto']
        leito = request.form['leito']

        foto = ''
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename!= '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Adiciona ID no nome pra não sobrescrever
                filename = f"{nome.replace(' ', '_')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                foto = f'fotos/{filename}'

        conn = get_db()
        conn.execute('INSERT INTO conviventes (nome, quarto, leito, foto) VALUES (?,?,?,?)',
                     (nome, quarto, leito, foto))
        conn.commit()
        conn.close()
        flash('Convivente cadastrado com sucesso!')
        return redirect(url_for('conviventes'))

    return render_template('novo_convivente.html', quarto=quarto)

@app.route('/editar_convivente/<int:id>', methods=['POST'])
def editar_convivente(id):
    nome = request.form['nome']

    conn = get_db()
    convivente = conn.execute('SELECT * FROM conviventes WHERE id =?', (id,)).fetchone()

    foto = convivente['foto'] # Mantém a foto antiga se não enviar nova

    if 'foto' in request.files:
        file = request.files['foto']
        if file and file.filename!= '' and allowed_file(file.filename):
            # Apaga foto antiga se existir
            if convivente['foto'] and os.path.exists(os.path.join('static', convivente['foto'])):
                try:
                    os.remove(os.path.join('static', convivente['foto']))
                except:
                    pass

            filename = secure_filename(file.filename)
            filename = f"{nome.replace(' ', '_')}_{id}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            foto = f'fotos/{filename}'

    conn.execute('UPDATE conviventes SET nome =?, foto =? WHERE id =?',
                 (nome, foto, id))
    conn.commit()
    conn.close()
    flash('Convivente atualizado com sucesso!')
    return redirect(url_for('conviventes'))

@app.route('/desocupar_convivente/<int:id>', methods=['POST'])
def desocupar_convivente(id):
    conn = get_db()
    convivente = conn.execute('SELECT * FROM conviventes WHERE id =?', (id,)).fetchone()

    # Apaga foto antiga se existir
    if convivente['foto'] and os.path.exists(os.path.join('static', convivente['foto'])):
        try:
            os.remove(os.path.join('static', convivente['foto']))
        except:
            pass

    # Limpa nome e foto, mas mantém quarto/leito
    conn.execute('UPDATE conviventes SET nome =?, foto =? WHERE id =?',
                 ('VAGO', '', id))
    conn.commit()
    conn.close()
    flash('Leito desocupado!')
    return redirect(url_for('conviventes'))

@app.route('/excluir_convivente/<int:id>', methods=['POST'])
def excluir_convivente(id):
    conn = get_db()
    convivente = conn.execute('SELECT * FROM conviventes WHERE id =?', (id,)).fetchone()

    # Apaga foto se existir
    if convivente['foto'] and os.path.exists(os.path.join('static', convivente['foto'])):
        try:
            os.remove(os.path.join('static', convivente['foto']))
        except:
            pass

    conn.execute('DELETE FROM conviventes WHERE id =?', (id,))
    conn.commit()
    conn.close()
    flash('Convivente excluído!')
    return redirect(url_for('conviventes'))

# Suas outras rotas continuam aqui embaixo...
# @app.route('/medicamentos')...
# @app.route('/relatorios')...
# etc

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
