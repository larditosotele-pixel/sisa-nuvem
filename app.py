@app.route('/exportar_mapeamento')
def exportar_mapeamento():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute('''
        SELECT
            q.numero as quarto_numero,
            l.numero_leito,
            c.nome as convivente_nome,
            CASE
                WHEN q.numero IN (1,2,3) THEN 'AMB1'
                WHEN q.numero IN (4,5,6,7) THEN 'AMB2_H'
                WHEN q.numero IN (8,9,10,11) THEN 'AMB2_M'
                WHEN q.numero IN (12,13,14,15) THEN 'AMB3_H'
                WHEN q.numero IN (16,17) THEN 'AMB3_M'
                ELSE 'OUTRO'
            END as ambiente_tipo
        FROM quartos q
        LEFT JOIN leitos l ON q.id = l.quarto_id
        LEFT JOIN conviventes c ON l.id = c.leito_id AND c.ativo = TRUE
        ORDER BY q.numero, CASE WHEN l.numero_leito ~ '^[0-9]+$' THEN CAST(l.numero_leito AS INTEGER) ELSE 999 END
    ''')

    dados_raw = cur.fetchall()
    cur.close()
    conn.close()

    quartos_dict = {}
    for row in dados_raw:
        q_num = row['quarto_numero']
        if q_num not in quartos_dict:
            quartos_dict[q_num] = {
                'ambiente': row['ambiente_tipo'],
                'leitos': []
            }
        if row['numero_leito']:
            quartos_dict[q_num]['leitos'].append({
                'num': row['numero_leito'],
                'nome': row['convivente_nome'] or 'VAGO'
            })

    output = io.BytesIO()
    
    # CORES IGUAIS À SUA PLANILHA
    cor_amb1 = PatternFill(start_color='C6E0B4', end_color='C6E0B4', fill_type='solid') # Verde claro
    cor_amb2_h = PatternFill(start_color='BDD7EE', end_color='BDD7EE', fill_type='solid') # Azul claro homens
    cor_amb2_m = PatternFill(start_color='F8CBAD', end_color='F8CBAD', fill_type='solid') # Laranja mulheres
    cor_amb3_h = PatternFill(start_color='BDD7EE', end_color='BDD7EE', fill_type='solid') # Azul claro
    cor_amb3_m = PatternFill(start_color='A9D08E', end_color='A9D08E', fill_type='solid') # Verde
    cor_cabecalho = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    cor_vago = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    borda = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    fonte_branca = Font(color='FFFFFF', bold=True)
    centro = Alignment(horizontal='center', vertical='center')

    linhas = []
    max_leitos = max([len(q['leitos']) for q in quartos_dict.values()]) if quartos_dict else 8

    # MONTA LAYOUT 4 QUARTOS POR LINHA
    def add_bloco_quartos(titulo, quartos_nums):
        linhas.append([titulo] + [f'QUARTO {q}' for q in quartos_nums])
        for i in range(max_leitos):
            linha = [f'LEITO {i+1}']
            for q in quartos_nums:
                if q in quartos_dict and i < len(quartos_dict[q]['leitos']):
                    linha.append(quartos_dict[q]['leitos'][i]['nome'])
                else:
                    linha.append('')
            linhas.append(linha)

    add_bloco_quartos('AMB 1', [1, 2, 3])
    add_bloco_quartos('AMB 2', [4, 5, 6, 7])
    add_bloco_quartos('AMB 2', [8, 9, 10, 11])
    add_bloco_quartos('AMB 3', [12, 13, 14, 15])
    add_bloco_quartos('AMB 3', [16, 17])

    df = pd.DataFrame(linhas)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, header=False, sheet_name='MAPEAMENTO')
        worksheet = writer.sheets['MAPEAMENTO']

        # APLICA CORES E FORMATAÇÃO
        row_idx = 1
        for linha in linhas:
            if linha[0].startswith('AMB'):
                for col in range(1, len(linha) + 1):
                    cell = worksheet.cell(row=row_idx, column=col)
                    cell.fill = cor_cabecalho
                    cell.font = fonte_branca
                    cell.alignment = centro
                    cell.border = borda
            else:
                for col in range(1, len(linha) + 1):
                    cell = worksheet.cell(row=row_idx, column=col)
                    cell.border = borda
                    cell.alignment = centro
                    if 'VAGO' in str(cell.value):
                        cell.fill = cor_vago
                    elif row_idx <= 9: # AMB1
                        cell.fill = cor_amb1
                    elif row_idx <= 18: # AMB2_H
                        cell.fill = cor_amb2_h
                    elif row_idx <= 27: # AMB2_M
                        cell.fill = cor_amb2_m
                    elif row_idx <= 36: # AMB3_H
                        cell.fill = cor_amb3_h
                    else: # AMB3_M
                        cell.fill = cor_amb3_m
            row_idx += 1

        for col in ['A', 'B', 'C', 'D', 'E']:
            worksheet.column_dimensions[col].width = 25

    # REMOVI O writer.close() DAQUI - ERA O BUG
    output.seek(0)
    data_hoje = datetime.now(fuso_sp).strftime('%d_%m_%Y')
    nome_arquivo = f'MAPEAMENTO_DE_LEITOS_CAE_IDOSOS_{data_hoje}.xlsx'
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=nome_arquivo)
