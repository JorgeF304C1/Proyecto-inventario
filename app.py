from flask import Flask, request, redirect, session, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = '123456'

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
"""basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'inventario.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False"""
#Se quito temporalmente

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
basedir = os.path.abspath(os.path.dirname(__file__))

# La variable DATABASE_URL la configuraremos en el servidor de PythonAnywhere.
# Si no la encuentra, usará la base de datos local sqlite para pruebas.
default_db_uri = 'sqlite:///' + os.path.join(basedir, 'inventario.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', default_db_uri)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS ---

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipo = db.Column(db.String(100), nullable=False)
    tipo_camiseta = db.Column(db.String(20), nullable=False)
    jugador = db.Column(db.String(100), nullable=False)
    dorsal = db.Column(db.String(10), nullable=True)
    talla = db.Column(db.String(10), nullable=False)
    cantidad = db.Column(db.Integer, default=0)

class Movimiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    usuario = db.Column(db.String(50), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_movimiento = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.String(255))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    anulado = db.Column(db.Boolean, default=False) 

# Helper para convertir productos a dict
def producto_to_dict(p):
    return {
        "id": p.id, "equipo": p.equipo, "tipo_camiseta": p.tipo_camiseta,
        "jugador": p.jugador, "dorsal": p.dorsal, "talla": p.talla, "cantidad": p.cantidad
    }

# --- RUTAS ---

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    Usuarios = {'jorge': '1234', 'karim': '1234'}
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in Usuarios and Usuarios[username] == password:
            session['username'] = username
            return redirect('/dashboard')
        else:
            error = "Credenciales incorrectas, intente de nuevo."
    return render_template('index.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    
    total_ventas = db.session.query(
        db.func.sum(Movimiento.precio_movimiento)
    ).filter(Movimiento.anulado == False).scalar() or 0
    
    return render_template('dashboard.html', total_ventas=total_ventas)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/nueva_venta')
def nueva_venta():
    if 'username' not in session:
        return redirect('/')
    productos = Producto.query.all()
    productos_serializados = [producto_to_dict(p) for p in productos]
    return render_template('new-sale.html', productos=productos_serializados)

@app.route('/registrar_venta', methods=['POST'])
def registrar_venta():
    if 'username' not in session:
        return redirect('/')

    try:
        data = request.json
        carrito = data.get("carrito", [])
        descripcion = data.get("descripcion", "")

        if not carrito:
            return jsonify({"error": "El carrito está vacío."}), 400

        # Verificar stock primero (sin modificar nada)
        for item in carrito:
            producto = Producto.query.filter_by(
                equipo=item["equipo"], tipo_camiseta=item["tipo_camiseta"],
                jugador=item["jugador"], talla=item["talla"]
            ).first()
            if not producto or producto.cantidad < item["cantidad"]:
                return jsonify({"error": f"Stock insuficiente para {item['jugador']} talla {item['talla']}"}), 400

        # Procesar venta
        for item in carrito:
            producto = Producto.query.filter_by(
                equipo=item["equipo"], tipo_camiseta=item["tipo_camiseta"],
                jugador=item["jugador"], talla=item["talla"]
            ).first()
            producto.cantidad -= item["cantidad"]

            movimiento = Movimiento(
                producto_id=producto.id,
                usuario=session['username'],
                cantidad=item["cantidad"],
                precio_movimiento=item["precio_total"],
                descripcion=descripcion
            )
            db.session.add(movimiento)

        db.session.commit()
        return jsonify({"mensaje": "Venta registrada correctamente."})

    except Exception as e:
        db.session.rollback()  # <-- Revertir cambios en caso de error
        return jsonify({"error": f"Error al registrar la venta: {str(e)}"}), 500

@app.route('/inventario')
def inventario():
    if 'username' not in session:
        return redirect('/')
    productos = Producto.query.all()
    return render_template('inventario.html', productos=productos)

@app.route('/movimientos')
def movimientos():
    if 'username' not in session:
        return redirect('/')
    
    movimientos = (
        db.session.query(
            Movimiento,
            Producto.equipo,
            Producto.jugador,
            Producto.talla
        )
        .join(Producto, Movimiento.producto_id == Producto.id)
        .filter(Movimiento.anulado == False)
        .order_by(Movimiento.fecha.desc())  # <-- Ordenar por fecha (más nuevos primero)
        .all()
    )
    
    return render_template('movimientos.html', movimientos=movimientos)

@app.route('/anular_movimiento/<int:id_movimiento>', methods=['POST'])
def anular_movimiento(id_movimiento):
    if 'username' not in session:
        return redirect('/')
    
    movimiento = Movimiento.query.get_or_404(id_movimiento)
    
    if movimiento.anulado:
        return jsonify({'error': 'Este movimiento ya está anulado'}), 400
    
    movimiento.anulado = True
    producto = Producto.query.get(movimiento.producto_id)
    producto.cantidad += movimiento.cantidad
    
    try:
        db.session.commit()
        # Calcular nuevo total después de anular
        nuevo_total = db.session.query(
            db.func.sum(Movimiento.precio_movimiento)
        ).filter(Movimiento.anulado == False).scalar() or 0
        
        return jsonify({
            'success': 'Movimiento anulado correctamente',
            'nuevo_total': nuevo_total
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
# --- BLOQUE DE INICIALIZACIÓN DE LA APP ---
if __name__ == '__main__':
   




    with app.app_context():
        db.create_all()
        
        if not Producto.query.first():
            print("Base de datos vacía, insertando inventario completo...")
            
            # CAMBIO: Aquí está tu lista completa de productos.
            productos_iniciales = [
         # Barcelona Local
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Lamine Yamal", dorsal="10", talla="S", cantidad=3),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Lamine Yamal", dorsal="10", talla="M", cantidad=5),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Lamine Yamal", dorsal="10", talla="L", cantidad=5),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Lamine Yamal", dorsal="10", talla="XL", cantidad=2),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Rashford", dorsal="14", talla="S", cantidad=2),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Rashford", dorsal="14", talla="M", cantidad=3),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Rashford", dorsal="14", talla="L", cantidad=3),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Rashford", dorsal="14", talla="XL", cantidad=1),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Pedri", dorsal="8", talla="S", cantidad=2),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Pedri", dorsal="8", talla="M", cantidad=3),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Pedri", dorsal="8", talla="L", cantidad=3),
         Producto(equipo="Barcelona", tipo_camiseta="local", jugador="Pedri", dorsal="8", talla="XL", cantidad=1),
         # Barcelona Visitante
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Lamine Yamal", dorsal="10", talla="S", cantidad=2),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Lamine Yamal", dorsal="10", talla="M", cantidad=5),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Lamine Yamal", dorsal="10", talla="L", cantidad=5),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Lamine Yamal", dorsal="10", talla="XL", cantidad=2),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Rashford", dorsal="14", talla="S", cantidad=2),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Rashford", dorsal="14", talla="M", cantidad=3),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Rashford", dorsal="14", talla="L", cantidad=3),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Rashford", dorsal="14", talla="XL", cantidad=1),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Pedri", dorsal="8", talla="S", cantidad=2),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Pedri", dorsal="8", talla="M", cantidad=3),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Pedri", dorsal="8", talla="L", cantidad=3),
         Producto(equipo="Barcelona", tipo_camiseta="visitante", jugador="Pedri", dorsal="8", talla="XL", cantidad=1),
         # Madrid Local
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Vini Jr", dorsal="7", talla="S", cantidad=2),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Vini Jr", dorsal="7", talla="M", cantidad=4),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Vini Jr", dorsal="7", talla="L", cantidad=3),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Vini Jr", dorsal="7", talla="XL", cantidad=1),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Mbappé", dorsal="10", talla="S", cantidad=2),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Mbappé", dorsal="10", talla="M", cantidad=4),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Mbappé", dorsal="10", talla="L", cantidad=3),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Mbappé", dorsal="10", talla="XL", cantidad=1),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Valverde", dorsal="8", talla="S", cantidad=2),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Valverde", dorsal="8", talla="M", cantidad=4),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Valverde", dorsal="8", talla="L", cantidad=3),
         Producto(equipo="Madrid", tipo_camiseta="local", jugador="Valverde", dorsal="8", talla="XL", cantidad=1),
         # Madrid Visitante
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Vini Jr", dorsal="7", talla="S", cantidad=2),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Vini Jr", dorsal="7", talla="M", cantidad=4),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Vini Jr", dorsal="7", talla="L", cantidad=3),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Vini Jr", dorsal="7", talla="XL", cantidad=1),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Mbappé", dorsal="10", talla="S", cantidad=2),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Mbappé", dorsal="10", talla="M", cantidad=4),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Mbappé", dorsal="10", talla="L", cantidad=3),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Mbappé", dorsal="10", talla="XL", cantidad=1),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Valverde", dorsal="8", talla="S", cantidad=2),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Valverde", dorsal="8", talla="M", cantidad=4),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Valverde", dorsal="8", talla="L", cantidad=3),
         Producto(equipo="Madrid", tipo_camiseta="visitante", jugador="Valverde", dorsal="8", talla="XL", cantidad=1),
         # Camisetas para niños
         Producto(equipo="Barcelona", tipo_camiseta="niños", jugador="Lamine Yamal", dorsal="10", talla="16", cantidad=10),
         Producto(equipo="Barcelona", tipo_camiseta="niños", jugador="Pedri", dorsal="8", talla="16", cantidad=5),
         Producto(equipo="Madrid", tipo_camiseta="niños", jugador="Mbappé", dorsal="10", talla="16", cantidad=10),
         Producto(equipo="Madrid", tipo_camiseta="niños", jugador="Vini Jr", dorsal="7", talla="16", cantidad=5),
       ]
            db.session.bulk_save_objects(productos_iniciales)
            db.session.commit()
            print("¡Inventario completo insertado!") 

# app.run(debug=True) Se quita temporalmente