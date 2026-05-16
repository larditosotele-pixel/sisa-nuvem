import os
from app import app, db, Convivente

def importar_conviventes():
    pasta_uploads = 'uploads'
    with app.app_context():
        db.session.query(Convivente).delete() # Limpa os 4 de teste
        
        for nome_arquivo in os.listdir(pasta_uploads):
            if nome_arquivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    partes = nome_arquivo.split('_')
                    quarto = int(partes[0].replace('q', ''))
                    leito = partes[1].replace('l', '').upper()
                    nome = ' '.join(partes[2:]).replace('.jpg', '').replace('.png', '').replace('.jpeg', '').replace('_', ' ')
                    
                    caminho_foto = f'/uploads/{nome_arquivo}'
                    
                    novo = Convivente(
                        nome=nome,
                        quarto=quarto,
                        leito=leito,
                        foto=caminho_foto
                    )
                    db.session.add(novo)
                    print(f'Cadastrado: Quarto {quarto} Leito {leito} - {nome}')
                except Exception as e:
                    print(f'Erro no arquivo {nome_arquivo}: {e}')
        
        db.session.commit()
        total = Convivente.query.count()
        print(f'\nFinalizado! Total de {total} conviventes importados.')

if __name__ == '__main__':
    importar_conviventes()