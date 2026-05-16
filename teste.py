from app import app, db, Convivente
with app.app_context():
    resultado = Convivente.query.all()
    print("Resultado:", resultado)
    print("Total:", len(resultado))