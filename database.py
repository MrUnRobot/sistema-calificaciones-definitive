from pymongo import MongoClient
import os

def conectar_mongodb():
    try:
        # Usa variable de entorno o local
        mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
        cliente = MongoClient(mongo_uri)
        db = cliente['sistema_calificaciones']
        return db
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None