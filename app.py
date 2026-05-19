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
            # Pega o número do quarto pra voltar pra âncora certa
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

        # Volta pro mapa na âncora do quarto
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
        # Pega o quarto antes de fazer qualquer coisa
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
