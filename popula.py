from app import app, db, Convivente
with app.app_context():
    db.session.add_all([
        Convivente(nome='Joao da Silva', quarto=1, leito='A', foto='/static/sem_foto.png'),
        Convivente(nome='Maria Souza', quarto=1, leito='B', foto='/static/sem_foto.png'),
        Convivente(nome='Jose Santos', quarto=2, leito='A', foto='/static/sem_foto.png'),
        Convivente(nome='Ana Lima', quarto=2, leito='B', foto='/static/sem_foto.png')
    ])
    db.session.commit()
    print("Cadastrei 4 conviventes de teste")