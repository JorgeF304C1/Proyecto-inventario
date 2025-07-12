from flask import Flask,request,redirect,session,render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime



app = Flask(__name__)
app.secret_key = '123456'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventario.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Modelos
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    cantidad = db.Column(db.Integer, default=0)

class Movimiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    usuario = db.Column(db.String(50), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.String(255))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

# Crear tablas y cargar productos una vez
with app.app_context():
    db.create_all()

    if not Producto.query.first():
        producto1 = Producto(nombre='Camiseta Real Madrid', cantidad=10)
        producto2 = Producto(nombre='Camiseta Barcelona', cantidad=8)
        db.session.add_all([producto1, producto2])
        db.session.commit()











@app.route('/', methods=['GET', 'POST'])

def login():

    Usuarios = {'jorge': '1234', 'karim': '1234'}

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in Usuarios and Usuarios[username] == password:
            session['username'] = username
            return redirect('/dashboard')
        else:
            return "Credenciales incorrectas, intente de nuevo."
    
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return f"Bienvenido {session['username']} al dashboard."
    else:
        return redirect('/')
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')





