from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import secrets
from flask_cors import CORS
from flask_session import Session  
import mysql.connector
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt


app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

# 🔧 Configuración de sesión persistente
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_FILE_DIR"] = "./flask_session"
app.config["SESSION_USE_SIGNER"] = True  
app.config["SESSION_KEY_PREFIX"] = "coquito_"  

Session(app)  # Inicializar sesión

CORS(app, resources={r"/*": {"origins": "http://127.0.0.1:5501"}}, supports_credentials=True)

# 🔧 Configuración de MySQL
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "Coquito"
}

def conectar_db():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"❌ Error al conectar a MySQL: {err}")
        return None

@app.route('/')
def index():
    return render_template('evaluacion.html')

@app.route('/guardar', methods=['POST'])
def guardar():
    try:
        datos = request.json  
        print(f"📩 Datos recibidos: {datos}")  

        if not datos:
            raise ValueError("No se recibieron datos en la solicitud")

        # Extraer valores
        campos_esperados = ["salud", "desarrollo_personal", "hogar", "familia_amigos", "amor", "ocio", "trabajo", "dinero"]
        valores = [int(datos.get(campo, 0)) for campo in campos_esperados]

        if any(v is None for v in valores):
            raise ValueError("Faltan valores en la solicitud")

        # Guardar en MySQL
        if not guardar_en_mysql(*valores):
            raise Exception("Error al guardar en la base de datos")

        # Calcular el promedio
        promedio = sum(valores) / len(valores)

        # 🔥 Guardar en la sesión y forzar actualización
        session['promedio'] = float(promedio)  
        session['valores'] = valores
        session.modified = True  # 🔥 Asegurar que se guarde
        print(f"✅ Sesión guardada ANTES de redirigir: {dict(session)}")

        # Generar gráfica
        generar_grafico(valores)

        return redirect(url_for('resultado'))

    except Exception as e:
        print("❌ Error en guardar:", str(e))
        return jsonify({"error": str(e)}), 500


def guardar_en_mysql(*valores):
    conexion = conectar_db()
    if not conexion:
        return False

    try:
        cursor = conexion.cursor()
        query = """
            INSERT INTO Encuesta (salud, desarrollo_personal, hogar, familia_amigos, amor, ocio, trabajo, dinero)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, valores)
        conexion.commit()
        print("✅ Datos guardados en MySQL")
        return True
    except mysql.connector.Error as err:
        print("❌ Error en MySQL:", str(err))
        return False
    finally:
        cursor.close()
        conexion.close()

def generar_grafico(valores):
    """Genera un gráfico de barras con los valores y lo guarda en la carpeta estática"""
    try:
        areas = ["Salud", "Desarrollo Personal", "Hogar", "Familia y Amigos", "Amor", "Ocio", "Trabajo", "Dinero"]
        image_path = os.path.join('static', 'img', 'grafico.png')
        os.makedirs(os.path.dirname(image_path), exist_ok=True)

        plt.figure(figsize=(8, 5))
        plt.bar(areas, valores, color='red')
        plt.title("Resultado de la Evaluación", fontsize=14)
        plt.xlabel("Área", fontsize=12)
        plt.ylabel("Valor", fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(image_path)
        plt.close()
        print(f"📊 Gráfico guardado en: {image_path}")

    except Exception as e:
        print("❌ Error al generar la gráfica:", str(e))

@app.route('/resultado')
def resultado():
    print(f"🔍 Estado de la sesión al entrar en /resultado: {dict(session)}")  

    if 'promedio' not in session or 'valores' not in session:
        return "Error: No hay datos en la sesión. Intenta ingresar nuevamente.", 400

    return render_template('resultado.html', promedio=session['promedio'], valores=session['valores'])


if __name__ == "__main__":
    os.makedirs("./flask_session", exist_ok=True)  # 🔥 Asegurar que el directorio existe
    app.run(debug=True, port=5000)
