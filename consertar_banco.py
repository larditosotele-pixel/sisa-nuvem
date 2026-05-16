from app import app, db
from sqlalchemy import text

with app.app_context():
    # Apaga só a tabela chamada errada
    db.session.execute(text('DROP TABLE IF EXISTS chamada'))
    db.session.commit()
    
    # Recria a tabela chamada com as colunas certas
    db.create_all()
    print("Tabela chamada corrigida! Conviventes mantidos intactos.")