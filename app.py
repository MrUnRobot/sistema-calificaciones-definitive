from flask import Flask, request, redirect, session, jsonify, send_from_directory
from pymongo import MongoClient
from datetime import datetime
import os
import bcrypt

app = Flask(__name__, template_folder='.', static_folder='static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'Kaliuserfr_2024_Escuela_20Nov_Sistema_Calif!@#$%^&*()')

# RUTA ESTÁTICA PARA SERVIR ARCHIVOS CSS, JS, IMÁGENES, ETC.
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# También crear una ruta específica para CSS por si acaso
@app.route('/css.css')
def serve_css():
    return send_from_directory('static', 'css.css')

def conectar_bd():
    try:
        # Obtener URI de MongoDB desde variables de entorno de Railway
        # Railway usa MONGO_URL o MONGODB_URI
        mongo_uri = os.environ.get('MONGO_URL') or os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/'
        
        # Conectar con timeout para Railway
        cliente = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
        db = cliente['sistema_calificaciones']
        
        # Verificar conexión (pero no fallar si no hay)
        try:
            cliente.server_info()
            print(f"✅ Conectado a MongoDB")
        except:
            print("⚠️  MongoDB: Conectado pero no se pudo verificar servidor")
        
        return db
    except Exception as e:
        print(f"⚠️  Error de conexión inicial a MongoDB: {e}")
        print("ℹ️  Se intentará reconectar cuando sea necesario")
        # No retornar None inmediatamente, intentar crear cliente básico
        try:
            cliente = MongoClient(mongo_uri, connect=False)
            db = cliente['sistema_calificaciones']
            return db
        except:
            return None

def obtener_proximo_id(coleccion):
    db = conectar_bd()
    if db is not None:
        ultimo = db[coleccion].find_one(sort=[("_id", -1)])
        return 1 if not ultimo else ultimo['_id'] + 1
    return 1

def calcular_promedio(calificaciones_trimestre):
    materias = ['matematicas', 'espanol', 'ingles', 'ciencias', 'formacion']
    suma = sum(float(calificaciones_trimestre.get(materia, 0)) for materia in materias)
    return round(suma / len(materias), 2)

def verificar_password(password, hash_password, es_admin=False):
    try:
        if es_admin:
            if isinstance(hash_password, str):
                hash_password = hash_password.encode('utf-8')
            return bcrypt.checkpw(password.encode('utf-8'), hash_password)
        else:
            return password == hash_password
    except Exception as e:
        print(f"❌ Error verificando password: {e}")
        return False

def agregar_mensaje(mensaje, tipo='success'):
    if 'mensajes' not in session:
        session['mensajes'] = []
    session['mensajes'].append({'texto': mensaje, 'tipo': tipo})
    session.modified = True

def obtener_mensajes():
    mensajes = session.get('mensajes', [])
    session['mensajes'] = []
    session.modified = True
    return mensajes

# Página de Login
@app.route('/')
def login():
    html = '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Sistema de Calificaciones</title>
        <link rel="stylesheet" href="/static/css.css">
    </head>
    <body>
        <div class="login-container">
            <div class="login-box">
                <div class="login-header">
                    <h1>🏫 Sistema de Calificaciones</h1>
                    <p>Escuela "20 de noviembre"</p>
                </div>
                <form action="/iniciar_sesion" method="POST" class="student-form">
                    <input type="text" name="usuario" placeholder="Usuario" required>
                    <input type="password" name="password" placeholder="Contraseña" required>
                    <button type="submit" class="btn btn-primary">Ingresar al Sistema</button>
                </form>
                <div style="margin-top: 1rem; text-align: center; font-size: 0.9rem;">
                    <p><strong>Credenciales de prueba:</strong></p>
                    <p>Admin: <code>admin</code> | Contraseña: <code>AdminSeguro2025!</code></p>
                    <p>Maestro 1°A: <code>m1a</code> | Contraseña: <code>1234</code></p>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    
    mensajes_html = ""
    for mensaje in obtener_mensajes():
        mensajes_html += f'<div class="alert alert-{mensaje["tipo"]}">{mensaje["texto"]}</div>'
    
    if mensajes_html:
        html = html.replace('<form action=', f'{mensajes_html}<form action=')
    
    return html

@app.route('/iniciar_sesion', methods=['POST'])
def iniciar_sesion():
    usuario = request.form['usuario']
    password = request.form['password']
    
    db = conectar_bd()
    if db is not None:
        maestro = db.maestros.find_one({'usuario': usuario, 'activo': True})
        if maestro:
            es_admin = maestro.get('rol') == 'admin'
            if verificar_password(password, maestro['password'], es_admin):
                session['usuario'] = usuario
                session['logueado'] = True
                session['maestro_id'] = maestro['_id']
                session['maestro_nombre'] = maestro['nombre']
                session['grupo'] = maestro['grupo']
                session['grado'] = maestro['grado']
                session['rol'] = maestro.get('rol', 'maestro')
                
                if es_admin:
                    agregar_mensaje(f"✅ Sesión de administrador iniciada correctamente", 'success')
                    return redirect('/admin')
                else:
                    agregar_mensaje(f"✅ Sesión iniciada correctamente - {maestro['nombre']} ({maestro['grupo']})", 'success')
                    return redirect('/seleccionar_trimestre')
        else:
            print(f"❌ Usuario no encontrado: {usuario}")
    
    agregar_mensaje("❌ Usuario o contraseña incorrectos", 'danger')
    return redirect('/')

# Selección de trimestre para maestros
@app.route('/seleccionar_trimestre')
def seleccionar_trimestre():
    if not session.get('logueado') or session.get('rol') == 'admin':
        return redirect('/')
    
    html = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Seleccionar Trimestre</title>
        <link rel="stylesheet" href="/static/css.css">
    </head>
    <body>
        <div class="login-container">
            <div class="login-box" style="max-width: 500px;">
                <div class="login-header">
                    <h1>📅 Seleccionar Trimestre</h1>
                    <p>Grupo: {session.get('grupo')}</p>
                    <p>Maestro: {session.get('maestro_nombre')}</p>
                </div>
                
                <div class="trimestre-options">
                    <a href="/calificaciones?trimestre=primer_trimestre" class="trimestre-card">
                        <div class="trimestre-icon">1️⃣</div>
                        <h3>Primer Trimestre</h3>
                        <p>Agosto - Noviembre</p>
                    </a>
                    
                    <a href="/calificaciones?trimestre=segundo_trimestre" class="trimestre-card">
                        <div class="trimestre-icon">2️⃣</div>
                        <h3>Segundo Trimestre</h3>
                        <p>Diciembre - Marzo</p>
                    </a>
                    
                    <a href="/calificaciones?trimestre=tercer_trimestre" class="trimestre-card">
                        <div class="trimestre-icon">3️⃣</div>
                        <h3>Tercer Trimestre</h3>
                        <p>Abril - Julio</p>
                    </a>
                </div>
                
                <div style="margin-top: 2rem; text-align: center;">
                    <a href="/cerrar_sesion" class="btn btn-danger">🚪 Cerrar Sesión</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

@app.route('/calificaciones')
def ver_calificaciones():
    if not session.get('logueado'):
        return redirect('/')
    
    # Obtener trimestre seleccionado
    trimestre_seleccionado = request.args.get('trimestre', 'primer_trimestre')
    session['trimestre_actual'] = trimestre_seleccionado
    
    grupo_maestro = session.get('grupo')
    es_admin = session.get('rol') == 'admin'
    
    db = conectar_bd()
    alumnos = []
    if db is not None:
        if es_admin:
            alumnos = list(db.alumnos.find().sort('grupo', 1).sort('apellidos', 1))
        else:
            alumnos = list(db.alumnos.find({'grupo': grupo_maestro}).sort('apellidos', 1))
    
    titulo_grupo = "Todos los Grupos (Admin)" if es_admin else grupo_maestro
    nombre_trimestre = trimestre_seleccionado.replace('_', ' ').title()
    
    # Obtener información del maestro para mostrar
    maestro_info = ""
    if not es_admin:
        # Para maestro normal, usar la información de la sesión
        maestro_info = f'👨‍🏫 {session.get("maestro_nombre")}'
    else:
        # Para admin, mostrar que es administrador
        maestro_info = '👨‍💼 Administrador del Sistema'
    
    html = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gestión de Calificaciones</title>
        <link rel="stylesheet" href="/static/css.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🏫 Calificaciones - {titulo_grupo}</h1>
                <div class="header-info">
                    <div class="info-card">
                        <span class="info-label">📅 Trimestre:</span>
                        <span class="info-value">{nombre_trimestre}</span>
                    </div>
                    <div class="info-card">
                        <span class="info-label">👨‍🏫 Maestro:</span>
                        <span class="info-value">{maestro_info}</span>
                    </div>
                    <div class="info-card">
                        <span class="info-label">👥 Grupo:</span>
                        <span class="info-value">{grupo_maestro if grupo_maestro != "Todos" else "Todos los grupos"}</span>
                    </div>
                </div>
                <nav>
                    <a href="/calificaciones?trimestre={trimestre_seleccionado}" class="btn">📝 Calificaciones</a>
                    <a href="/reportes" class="btn">📊 Reportes</a>
                    {'<a href="/admin" class="btn">👨‍💼 Admin</a>' if es_admin else ''}
                    {'<a href="/seleccionar_trimestre" class="btn">📅 Cambiar Trimestre</a>' if not es_admin else ''}
                    <a href="/cerrar_sesion" class="btn btn-danger">🚪 Cerrar Sesión</a>
                </nav>
            </header>

            <main>
    '''
    
    mensajes_html = ""
    for mensaje in obtener_mensajes():
        mensajes_html += f'<div class="alert alert-{mensaje["tipo"]}">{mensaje["texto"]}</div>'
    
    html += mensajes_html
    
    if es_admin:
        html += f'''
                <section class="form-section">
                    <h2>👥 Gestión de Alumnos - {grupo_maestro if grupo_maestro != "Todos" else "Todos los Grupos"}</h2>
                    <form action="/agregar_alumno" method="POST" class="student-form">
                        <input type="text" name="nombre" placeholder="Nombre del Alumno" required>
                        <input type="text" name="apellidos" placeholder="Apellidos del Alumno" required>
                        <select name="grupo" required>
                            <option value="">Selecciona grupo</option>
                            <option value="1°A">1°A</option>
                            <option value="1°B">1°B</option>
                            <option value="1°C">1°C</option>
                            <option value="2°A">2°A</option>
                            <option value="2°B">2°B</option>
                            <option value="2°C">2°C</option>
                            <option value="3°A">3°A</option>
                            <option value="3°B">3°B</option>
                            <option value="3°C">3°C</option>
                            <option value="4°A">4°A</option>
                            <option value="4°B">4°B</option>
                            <option value="4°C">4°C</option>
                            <option value="5°A">5°A</option>
                            <option value="5°B">5°B</option>
                            <option value="5°C">5°C</option>
                            <option value="6°A">6°A</option>
                            <option value="6°B">6°B</option>
                            <option value="6°C">6°C</option>
                        </select>
                        <button type="submit" class="btn btn-primary">➕ Agregar Alumno</button>
                    </form>
                </section>
        '''
    else:
        html += f'''
                <section class="form-section">
                    <div class="alert alert-info">
                        <strong>📅 Trimestre Actual:</strong> {nombre_trimestre} | 
                        <strong>👨‍🏫 Maestro:</strong> {session.get('maestro_nombre')} | 
                        <strong>👥 Grupo:</strong> {grupo_maestro}
                    </div>
                </section>
        '''
    
    html += f'''
                <section class="list-section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h2>📊 Calificaciones - {nombre_trimestre} (Total: {len(alumnos)})</h2>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    {'<th>Grupo</th>' if es_admin else ''}
                                    <th>Alumno</th>
                                    <th>Matemáticas</th>
                                    <th>Español</th>
                                    <th>Inglés</th>
                                    <th>Ciencias</th>
                                    <th>Formación Cívica</th>
                                    <th>Promedio</th>
                                    {'<th>Acciones</th>' if es_admin else ''}
                                </tr>
                            </thead>
                            <tbody>
    '''
    
    if alumnos:
        for alumno in alumnos:
            calificaciones = alumno['calificaciones'].get(trimestre_seleccionado, {})
            promedio = calcular_promedio(calificaciones)
            
            html += f'''
                                <tr class="fila-alumno" data-alumno-id="{alumno['_id']}">
                                    {'<td>' + alumno['grupo'] + '</td>' if es_admin else ''}
                                    <td>{alumno['nombre']} {alumno['apellidos']}</td>
                                    <td>{calificaciones.get('matematicas', 'N/A')}</td>
                                    <td>{calificaciones.get('espanol', 'N/A')}</td>
                                    <td>{calificaciones.get('ingles', 'N/A')}</td>
                                    <td>{calificaciones.get('ciencias', 'N/A')}</td>
                                    <td>{calificaciones.get('formacion', 'N/A')}</td>
                                    <td><strong>{promedio if promedio > 0 else 'N/A'}</strong></td>
            '''
            
            if es_admin:
                html += f'''
                                    <td>
                                        <button class="btn btn-warning btn-sm" onclick="abrirModalAdmin({alumno['_id']}, '{alumno['nombre']}', '{alumno['apellidos']}', '{alumno['grupo']}', {calificaciones.get('matematicas', 0)}, {calificaciones.get('espanol', 0)}, {calificaciones.get('ingles', 0)}, {calificaciones.get('ciencias', 0)}, {calificaciones.get('formacion', 0)})">✏️ Modificar</button>
                                        <form action="/eliminar_alumno/{alumno['_id']}" method="POST" style="display: inline;">
                                            <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('¿Estás seguro de eliminar a {alumno['nombre']} {alumno['apellidos']}?')">🗑️ Eliminar</button>
                                        </form>
                                    </td>
                '''
            else:
                html += f'''
                                    <td style="position: relative;">
                                        <div class="hover-actions">
                                            <button class="btn btn-warning btn-sm" onclick="abrirModalMaestro({alumno['_id']}, {calificaciones.get('matematicas', 0)}, {calificaciones.get('espanol', 0)}, {calificaciones.get('ingles', 0)}, {calificaciones.get('ciencias', 0)}, {calificaciones.get('formacion', 0)})">✏️ Modificar Calificaciones</button>
                                        </div>
                                    </td>
                '''
            
            html += '</tr>'
    else:
        html += '''
                                <tr>
                                    <td colspan="8" class="no-data">No hay alumnos registrados</td>
                                </tr>
        '''
    
    html += '''
                            </tbody>
                        </table>
                    </div>
                </section>
            </main>
        </div>
    '''
    
    if es_admin:
        html += '''
        <!-- Modal para Admin -->
        <div id="modalAdmin" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>✏️ Modificar Alumno y Calificaciones</h2>
                    <span class="close">&times;</span>
                </div>
                <form id="formModificarAdmin" method="POST" class="student-form">
                    <input type="hidden" id="admin_alumno_id" name="alumno_id">
                    
                    <div class="form-group">
                        <label for="admin_nombre">Nombre:</label>
                        <input type="text" id="admin_nombre" name="nombre" placeholder="Nombre del alumno" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="admin_apellidos">Apellidos:</label>
                        <input type="text" id="admin_apellidos" name="apellidos" placeholder="Apellidos del alumno" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="admin_grupo">Grupo:</label>
                        <select id="admin_grupo" name="grupo" required>
                            <option value="">Selecciona grupo</option>
                            <option value="1°A">1°A</option>
                            <option value="1°B">1°B</option>
                            <option value="1°C">1°C</option>
                            <option value="2°A">2°A</option>
                            <option value="2°B">2°B</option>
                            <option value="2°C">2°C</option>
                            <option value="3°A">3°A</option>
                            <option value="3°B">3°B</option>
                            <option value="3°C">3°C</option>
                            <option value="4°A">4°A</option>
                            <option value="4°B">4°B</option>
                            <option value="4°C">4°C</option>
                            <option value="5°A">5°A</option>
                            <option value="5°B">5°B</option>
                            <option value="5°C">5°C</option>
                            <option value="6°A">6°A</option>
                            <option value="6°B">6°B</option>
                            <option value="6°C">6°C</option>
                        </select>
                    </div>
                    
                    <h3 style="grid-column: 1 / -1; margin-top: 1rem;">📚 Calificaciones (5-10)</h3>
                    
                    <div class="materia-group">
                        <label for="admin_matematicas">🔢 Matemáticas:</label>
                        <input type="number" id="admin_matematicas" name="matematicas" min="5" max="10" step="0.1" required>
                    </div>
                    
                    <div class="materia-group">
                        <label for="admin_espanol">📚 Español:</label>
                        <input type="number" id="admin_espanol" name="espanol" min="5" max="10" step="0.1" required>
                    </div>
                    
                    <div class="materia-group">
                        <label for="admin_ingles">🌐 Inglés:</label>
                        <input type="number" id="admin_ingles" name="ingles" min="5" max="10" step="0.1" required>
                    </div>
                    
                    <div class="materia-group">
                        <label for="admin_ciencias">🔬 Ciencias:</label>
                        <input type="number" id="admin_ciencias" name="ciencias" min="5" max="10" step="0.1" required>
                    </div>
                    
                    <div class="materia-group">
                        <label for="admin_formacion">⭐ Formación Cívica:</label>
                        <input type="number" id="admin_formacion" name="formacion" min="5" max="10" step="0.1" required>
                    </div>
                    
                    <div class="modal-actions">
                        <button type="button" class="btn btn-secondary" onclick="cerrarModalAdmin()">Cancelar</button>
                        <button type="submit" class="btn btn-primary">Guardar Cambios</button>
                    </div>
                </form>
            </div>
        </div>
        '''
    else:
        html += f'''
        <!-- Modal para Maestro -->
        <div id="modalMaestro" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>✏️ Modificar Calificaciones - {nombre_trimestre}</h2>
                    <span class="close">&times;</span>
                </div>
                <form id="formModificarMaestro" method="POST" class="student-form">
                    <input type="hidden" id="maestro_alumno_id" name="alumno_id">
                    <input type="hidden" name="trimestre" value="{trimestre_seleccionado}">
                    
                    <h3 style="grid-column: 1 / -1; margin-bottom: 1rem;">📚 Calificaciones (5-10)</h3>
                    
                    <div class="materia-group">
                        <label for="maestro_matematicas">🔢 Matemáticas:</label>
                        <input type="number" id="maestro_matematicas" name="matematicas" min="5" max="10" step="0.1" required>
                    </div>
                    
                    <div class="materia-group">
                        <label for="maestro_espanol">📚 Español:</label>
                        <input type="number" id="maestro_espanol" name="espanol" min="5" max="10" step="0.1" required>
                    </div>
                    
                    <div class="materia-group">
                        <label for="maestro_ingles">🌐 Inglés:</label>
                        <input type="number" id="maestro_ingles" name="ingles" min="5" max="10" step="0.1" required>
                    </div>
                    
                    <div class="materia-group">
                        <label for="maestro_ciencias">🔬 Ciencias:</label>
                        <input type="number" id="maestro_ciencias" name="ciencias" min="5" max="10" step="0.1" required>
                    </div>
                    
                    <div class="materia-group">
                        <label for="maestro_formacion">⭐ Formación Cívica:</label>
                        <input type="number" id="maestro_formacion" name="formacion" min="5" max="10" step="0.1" required>
                    </div>
                    
                    <div class="modal-actions">
                        <button type="button" class="btn btn-secondary" onclick="cerrarModalMaestro()">Cancelar</button>
                        <button type="submit" class="btn btn-primary">Guardar Calificaciones</button>
                    </div>
                </form>
            </div>
        </div>
        '''
    
    html += '''
        <script>
            // Funciones para modales de Admin
            function abrirModalAdmin(id, nombre, apellidos, grupo, matematicas, espanol, ingles, ciencias, formacion) {
                document.getElementById("admin_alumno_id").value = id;
                document.getElementById("admin_nombre").value = nombre;
                document.getElementById("admin_apellidos").value = apellidos;
                document.getElementById("admin_grupo").value = grupo;
                document.getElementById("admin_matematicas").value = matematicas;
                document.getElementById("admin_espanol").value = espanol;
                document.getElementById("admin_ingles").value = ingles;
                document.getElementById("admin_ciencias").value = ciencias;
                document.getElementById("admin_formacion").value = formacion;
                
                document.getElementById("formModificarAdmin").action = `/modificar_alumno/` + id;
                document.getElementById("modalAdmin").style.display = "block";
            }

            function cerrarModalAdmin() {
                document.getElementById("modalAdmin").style.display = "none";
            }

            // Funciones para modales de Maestro
            function abrirModalMaestro(id, matematicas, espanol, ingles, ciencias, formacion) {
                document.getElementById("maestro_alumno_id").value = id;
                document.getElementById("maestro_matematicas").value = matematicas;
                document.getElementById("maestro_espanol").value = espanol;
                document.getElementById("maestro_ingles").value = ingles;
                document.getElementById("maestro_ciencias").value = ciencias;
                document.getElementById("maestro_formacion").value = formacion;
                
                document.getElementById("formModificarMaestro").action = `/modificar_calificaciones/` + id;
                document.getElementById("modalMaestro").style.display = "block";
            }

            function cerrarModalMaestro() {
                document.getElementById("modalMaestro").style.display = "none";
            }

            // Cerrar modales
            document.querySelectorAll('.close').forEach(closeBtn => {
                closeBtn.onclick = function() {
                    document.querySelectorAll('.modal').forEach(modal => {
                        modal.style.display = "none";
                    });
                }
            });

            window.onclick = function(event) {
                document.querySelectorAll('.modal').forEach(modal => {
                    if (event.target == modal) {
                        modal.style.display = "none";
                    }
                });
            }

            // Hover effects para filas de alumnos (maestros)
            document.querySelectorAll('.fila-alumno').forEach(fila => {
                fila.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = '#f8f9fa';
                    this.style.cursor = 'pointer';
                });
                
                fila.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = '';
                });
            });
        </script>
        
        <style>
            /* Estilos adicionales para los grupos de materias */
            .materia-group {
                display: grid;
                grid-template-columns: 120px 1fr;
                align-items: center;
                gap: 10px;
                margin-bottom: 15px;
            }
            
            .materia-group label {
                font-weight: bold;
                color: #333;
                font-size: 14px;
            }
            
            .materia-group input {
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            
            .form-group {
                margin-bottom: 15px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #333;
            }
            
            .form-group input,
            .form-group select {
                width: 100%;
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            
            /* Estilos para la información del encabezado */
            .header-info {
                display: flex;
                gap: 20px;
                margin: 15px 0;
                flex-wrap: wrap;
            }
            
            .info-card {
                background: #f8f9fa;
                padding: 10px 15px;
                border-radius: 8px;
                border-left: 4px solid #007bff;
                display: flex;
                flex-direction: column;
                min-width: 150px;
            }
            
            .info-label {
                font-size: 0.85rem;
                color: #6c757d;
                font-weight: 500;
            }
            
            .info-value {
                font-size: 1rem;
                color: #333;
                font-weight: 600;
                margin-top: 3px;
            }
        </style>
    </body>
    </html>
    '''
    
    return html

# ... (resto del código de las rutas se mantiene igual) ...

@app.route('/agregar_alumno', methods=['POST'])
def agregar_alumno():
    if not session.get('logueado') or session.get('rol') != 'admin':
        agregar_mensaje("❌ No tienes permisos para realizar esta acción", 'danger')
        return redirect('/calificaciones')
    
    nombre = request.form['nombre']
    apellidos = request.form['apellidos']
    grupo = request.form['grupo']
    
    if nombre and apellidos and grupo:
        db = conectar_bd()
        if db is not None:
            alumno_existente = db.alumnos.find_one({
                'nombre': nombre,
                'apellidos': apellidos,
                'grupo': grupo
            })
            
            if alumno_existente:
                agregar_mensaje(f"❌ El alumno {nombre} {apellidos} ya existe en el grupo {grupo}", 'danger')
            else:
                alumno_data = {
                    '_id': obtener_proximo_id('alumnos'),
                    'nombre': nombre,
                    'apellidos': apellidos,
                    'grupo': grupo,
                    'calificaciones': {
                        'primer_trimestre': {
                            'matematicas': 0, 'espanol': 0, 'ingles': 0, 'ciencias': 0, 'formacion': 0
                        },
                        'segundo_trimestre': {
                            'matematicas': 0, 'espanol': 0, 'ingles': 0, 'ciencias': 0, 'formacion': 0
                        },
                        'tercer_trimestre': {
                            'matematicas': 0, 'espanol': 0, 'ingles': 0, 'ciencias': 0, 'formacion': 0
                        }
                    },
                    'fecha_registro': datetime.now()
                }
                
                db.alumnos.insert_one(alumno_data)
                mensaje = f"✅ Alumno {nombre} {apellidos} agregado al grupo {grupo}"
                agregar_mensaje(mensaje, 'success')
                print(mensaje)
    
    return redirect('/calificaciones')

@app.route('/modificar_alumno/<int:alumno_id>', methods=['POST'])
def modificar_alumno(alumno_id):
    if not session.get('logueado') or session.get('rol') != 'admin':
        agregar_mensaje("❌ No tienes permisos para realizar esta acción", 'danger')
        return redirect('/calificaciones')
    
    nombre = request.form['nombre']
    apellidos = request.form['apellidos']
    grupo = request.form['grupo']
    trimestre_actual = session.get('trimestre_actual', 'primer_trimestre')
    
    calificaciones = {
        'matematicas': float(request.form['matematicas']),
        'espanol': float(request.form['espanol']),
        'ingles': float(request.form['ingles']),
        'ciencias': float(request.form['ciencias']),
        'formacion': float(request.form['formacion'])
    }
    
    for materia, calificacion in calificaciones.items():
        if calificacion < 5 or calificacion > 10:
            agregar_mensaje(f"❌ Las calificaciones deben estar entre 5 y 10", 'danger')
            return redirect('/calificaciones')
    
    db = conectar_bd()
    if db is not None:
        resultado = db.alumnos.update_one(
            {'_id': alumno_id},
            {
                '$set': {
                    'nombre': nombre,
                    'apellidos': apellidos,
                    'grupo': grupo,
                    f'calificaciones.{trimestre_actual}': calificaciones
                }
            }
        )
        
        if resultado.modified_count > 0:
            mensaje = f"✅ Alumno {nombre} {apellidos} modificado correctamente"
            agregar_mensaje(mensaje, 'success')
        else:
            mensaje = f"❌ No se pudo modificar el alumno"
            agregar_mensaje(mensaje, 'danger')
    
    return redirect('/calificaciones')

@app.route('/modificar_calificaciones/<int:alumno_id>', methods=['POST'])
def modificar_calificaciones(alumno_id):
    if not session.get('logueado') or session.get('rol') == 'admin':
        agregar_mensaje("❌ No tienes permisos para realizar esta acción", 'danger')
        return redirect('/calificaciones')
    
    trimestre = request.form['trimestre']
    
    calificaciones = {
        'matematicas': float(request.form['matematicas']),
        'espanol': float(request.form['espanol']),
        'ingles': float(request.form['ingles']),
        'ciencias': float(request.form['ciencias']),
        'formacion': float(request.form['formacion'])
    }
    
    for materia, calificacion in calificaciones.items():
        if calificacion < 5 or calificacion > 10:
            agregar_mensaje(f"❌ Las calificaciones deben estar entre 5 y 10", 'danger')
            return redirect('/calificaciones')
    
    db = conectar_bd()
    if db is not None:
        alumno = db.alumnos.find_one({'_id': alumno_id})
        if alumno:
            resultado = db.alumnos.update_one(
                {'_id': alumno_id},
                {
                    '$set': {
                        f'calificaciones.{trimestre}': calificaciones
                    }
                }
            )
            
            if resultado.modified_count > 0:
                mensaje = f"✅ Calificaciones de {alumno['nombre']} {alumno['apellidos']} actualizadas"
                agregar_mensaje(mensaje, 'success')
            else:
                mensaje = f"❌ No se pudieron actualizar las calificaciones"
                agregar_mensaje(mensaje, 'danger')
    
    return redirect('/calificaciones?trimestre=' + trimestre)

@app.route('/eliminar_alumno/<int:alumno_id>', methods=['POST'])
def eliminar_alumno(alumno_id):
    if not session.get('logueado') or session.get('rol') != 'admin':
        agregar_mensaje("❌ No tienes permisos para realizar esta acción", 'danger')
        return redirect('/calificaciones')
    
    db = conectar_bd()
    if db is not None:
        alumno = db.alumnos.find_one({'_id': alumno_id})
        if alumno:
            resultado = db.alumnos.delete_one({'_id': alumno_id})
            if resultado.deleted_count > 0:
                mensaje = f"✅ Alumno {alumno['nombre']} {alumno['apellidos']} eliminado correctamente"
                agregar_mensaje(mensaje, 'success')
            else:
                mensaje = f"❌ Error al eliminar el alumno"
                agregar_mensaje(mensaje, 'danger')
    
    return redirect('/calificaciones')

@app.route('/reportes')
def reportes():
    if not session.get('logueado'):
        return redirect('/')
    
    es_admin = session.get('rol') == 'admin'
    grupo_maestro = session.get('grupo')
    
    # Obtener información del maestro
    maestro_info = ""
    if not es_admin:
        maestro_info = f'👨‍🏫 {session.get("maestro_nombre")}'
    else:
        maestro_info = '👨‍💼 Administrador del Sistema'
    
    html = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reportes - Sistema de Calificaciones</title>
        <link rel="stylesheet" href="/static/css.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>📊 Reportes de Calificaciones</h1>
                <div class="header-info">
                    <div class="info-card">
                        <span class="info-label">👨‍🏫 Maestro:</span>
                        <span class="info-value">{maestro_info}</span>
                    </div>
                    <div class="info-card">
                        <span class="info-label">👥 Grupo:</span>
                        <span class="info-value">{grupo_maestro if grupo_maestro != "Todos" else "Todos los grupos"}</span>
                    </div>
                </div>
                <nav>
                    <a href="/calificaciones" class="btn">📝 Calificaciones</a>
                    <a href="/reportes" class="btn">📊 Reportes</a>
                    {'<a href="/admin" class="btn">👨‍💼 Admin</a>' if es_admin else ''}
                    <a href="/cerrar_sesion" class="btn btn-danger">🚪 Cerrar Sesión</a>
                </nav>
            </header>

            <main>
                <section class="form-section">
                    <h2>🔍 Seleccionar Grupo y Trimestre</h2>
                    <form action="/reportes" method="GET" class="student-form">
                        {'<select name="grupo" required>' if es_admin else ''}
                            {'<option value="">Selecciona grupo</option>' if es_admin else ''}
                            {'<option value="1°A">1°A</option>' if es_admin else ''}
                            {'<option value="1°B">1°B</option>' if es_admin else ''}
                            {'<option value="1°C">1°C</option>' if es_admin else ''}
                            {'<option value="2°A">2°A</option>' if es_admin else ''}
                            {'<option value="2°B">2°B</option>' if es_admin else ''}
                            {'<option value="2°C">2°C</option>' if es_admin else ''}
                            {'<option value="3°A">3°A</option>' if es_admin else ''}
                            {'<option value="3°B">3°B</option>' if es_admin else ''}
                            {'<option value="3°C">3°C</option>' if es_admin else ''}
                            {'<option value="4°A">4°A</option>' if es_admin else ''}
                            {'<option value="4°B">4°B</option>' if es_admin else ''}
                            {'<option value="4°C">4°C</option>' if es_admin else ''}
                            {'<option value="5°A">5°A</option>' if es_admin else ''}
                            {'<option value="5°B">5°B</option>' if es_admin else ''}
                            {'<option value="5°C">5°C</option>' if es_admin else ''}
                            {'<option value="6°A">6°A</option>' if es_admin else ''}
                            {'<option value="6°B">6°B</option>' if es_admin else ''}
                            {'<option value="6°C">6°C</option>' if es_admin else ''}
                        {'</select>' if es_admin else ''}
                        
                        <select name="trimestre" required>
                            <option value="primer_trimestre">Primer Trimestre</option>
                            <option value="segundo_trimestre">Segundo Trimestre</option>
                            <option value="tercer_trimestre">Tercer Trimestre</option>
                        </select>
                        
                        <button type="submit" class="btn btn-primary">🔍 Ver Reporte</button>
                    </form>
                </section>
    '''
    
    grupo_seleccionado = request.args.get('grupo', grupo_maestro if not es_admin else '')
    trimestre_seleccionado = request.args.get('trimestre', 'primer_trimestre')
    
    if grupo_seleccionado:
        db = conectar_bd()
        alumnos = []
        if db is not None:
            if es_admin:
                alumnos = list(db.alumnos.find({'grupo': grupo_seleccionado}).sort('apellidos', 1))
            else:
                alumnos = list(db.alumnos.find({'grupo': grupo_maestro}).sort('apellidos', 1))
        
        nombre_trimestre = trimestre_seleccionado.replace('_', ' ').title()
        
        # Obtener el nombre del maestro del grupo seleccionado (para admin)
        maestro_grupo_info = ""
        if es_admin and grupo_seleccionado:
            maestro_grupo = db.maestros.find_one({'grupo': grupo_seleccionado})
            if maestro_grupo:
                maestro_grupo_info = f'👨‍🏫 {maestro_grupo["nombre"]}'
            else:
                maestro_grupo_info = '👨‍🏫 Maestro no asignado'
        elif not es_admin:
            maestro_grupo_info = maestro_info
        
        html += f'''
                <section class="list-section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <div>
                            <h2>📋 Reporte - {grupo_seleccionado} - {nombre_trimestre}</h2>
                            <div style="display: flex; gap: 15px; margin-top: 5px; font-size: 0.95rem; color: #666;">
                                <span><strong>👨‍🏫 Maestro:</strong> {maestro_grupo_info}</span>
                                <span><strong>📅 Trimestre:</strong> {nombre_trimestre}</span>
                                <span><strong>👥 Total alumnos:</strong> {len(alumnos)}</span>
                            </div>
                        </div>
                        <button onclick="window.print()" class="btn btn-primary">🖨️ Imprimir Reporte</button>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Alumno</th>
                                    <th>Matemáticas</th>
                                    <th>Español</th>
                                    <th>Inglés</th>
                                    <th>Ciencias</th>
                                    <th>Formación Cívica</th>
                                    <th>Promedio</th>
                                </tr>
                            </thead>
                            <tbody>
        '''
        
        if alumnos:
            for alumno in alumnos:
                calificaciones = alumno['calificaciones'].get(trimestre_seleccionado, {})
                promedio = calcular_promedio(calificaciones)
                
                html += f'''
                                <tr>
                                    <td>{alumno['nombre']} {alumno['apellidos']}</td>
                                    <td>{calificaciones.get('matematicas', 'N/A')}</td>
                                    <td>{calificaciones.get('espanol', 'N/A')}</td>
                                    <td>{calificaciones.get('ingles', 'N/A')}</td>
                                    <td>{calificaciones.get('ciencias', 'N/A')}</td>
                                    <td>{calificaciones.get('formacion', 'N/A')}</td>
                                    <td><strong>{promedio if promedio > 0 else 'N/A'}</strong></td>
                                </tr>
                '''
        else:
            html += '''
                                <tr>
                                    <td colspan="7" class="no-data">No hay alumnos en este grupo</td>
                                </tr>
            '''
        
        html += '''
                            </tbody>
                        </table>
                    </div>
                </section>
        '''
    
    html += '''
            </main>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/admin')
def admin_panel():
    if not session.get('logueado') or session.get('rol') != 'admin':
        return redirect('/')
    
    db = conectar_bd()
    estadisticas = {
        'total_maestros': 0,
        'total_alumnos': 0,
        'alumnos_por_grado': {}
    }
    
    if db is not None:
        estadisticas['total_maestros'] = db.maestros.count_documents({'rol': 'maestro', 'activo': True})
        estadisticas['total_alumnos'] = db.alumnos.count_documents({})
        
        for grado in range(1, 7):
            grupos = [f"{grado}°A", f"{grado}°B", f"{grado}°C"]
            estadisticas['alumnos_por_grado'][f'{grado}°'] = db.alumnos.count_documents({'grupo': {'$in': grupos}})
    
    html = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Panel Administrativo</title>
        <link rel="stylesheet" href="/static/css.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1>👨‍💼 Panel Administrativo</h1>
                <div class="header-info">
                    <div class="info-card">
                        <span class="info-label">👨‍💼 Usuario:</span>
                        <span class="info-value">Administrador del Sistema</span>
                    </div>
                    <div class="info-card">
                        <span class="info-label">📊 Maestros activos:</span>
                        <span class="info-value">{estadisticas['total_maestros']}</span>
                    </div>
                    <div class="info-card">
                        <span class="info-label">👥 Alumnos totales:</span>
                        <span class="info-value">{estadisticas['total_alumnos']}</span>
                    </div>
                </div>
                <nav>
                    <a href="/admin" class="btn">📊 Dashboard</a>
                    <a href="/calificaciones" class="btn">👥 Gestionar Alumnos</a>
                    <a href="/reportes" class="btn">📋 Reportes</a>
                    <a href="/cerrar_sesion" class="btn btn-danger">🚪 Cerrar Sesión</a>
                </nav>
            </header>

            <main>
    '''
    
    mensajes_html = ""
    for mensaje in obtener_mensajes():
        mensajes_html += f'<div class="alert alert-{mensaje["tipo"]}">{mensaje["texto"]}</div>'
    
    if mensajes_html:
        html += mensajes_html
    
    html += f'''
                <section class="form-section">
                    <h2>📈 Estadísticas del Sistema</h2>
                    <div class="student-details" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
                        <div style="text-align: center; padding: 1rem; background: #f8f9fa; border-radius: 10px;">
                            <h3>👨‍🏫 Maestros Activos</h3>
                            <p style="font-size: 2rem; font-weight: bold; color: #3498db;">{estadisticas['total_maestros']}</p>
                        </div>
                        <div style="text-align: center; padding: 1rem; background: #f8f9fa; border-radius: 10px;">
                            <h3>👥 Alumnos Registrados</h3>
                            <p style="font-size: 2rem; font-weight: bold; color: #27ae60;">{estadisticas['total_alumnos']}</p>
                        </div>
                    </div>
                </section>

                <section class="list-section">
                    <h2>📊 Alumnos por Grado</h2>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Grado</th>
                                    <th>Total Alumnos</th>
                                </tr>
                            </thead>
                            <tbody>
    '''
    
    for grado, total in estadisticas['alumnos_por_grado'].items():
        html += f'''
                                <tr>
                                    <td>{grado}</td>
                                    <td>{total}</td>
                                </tr>
        '''
    
    html += '''
                            </tbody>
                        </table>
                    </div>
                </section>
            </main>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear()
    agregar_mensaje("👋 Sesión cerrada correctamente", 'success')
    return redirect('/')

if __name__ == '__main__':
    # Solo para desarrollo local
    if not os.path.exists('static'):
        os.makedirs('static')
    
    port = int(os.environ.get("PORT", 5000))
    
    print(f"🚀 Sistema de Calificaciones - Modo Desarrollo")
    print(f"📡 http://localhost:{port}")
    print("👤 Admin: admin | Contraseña: AdminSeguro2025!")
    print("👨‍🏫 Maestro 1°A: m1a | Contraseña: 1234")
    

    app.run(debug=True, host='0.0.0.0', port=port)
