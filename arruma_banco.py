from app import app, db
import sqlite3

with app.app_context():
    # Conecta direto no sqlite
    conn = sqlite3.connect('lar_ditoso.db')
    cursor = conn.cursor()

    # Verifica se a coluna já existe
    cursor.execute("PRAGMA table_info(chamada)")
    colunas = [col[1] for col in cursor.fetchall()]

    if 'convivente_id' not in colunas:
        print("Adicionando coluna convivente_id...")
        cursor.execute("ALTER TABLE chamada ADD COLUMN convivente_id INTEGER")
        conn.commit()
        print("Coluna adicionada com sucesso!")
    else:
        print("Coluna já existe.")
    
    conn.close()