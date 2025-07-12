from flask import Flask,request,redirect,session,render_template

app = Flask(__name__)
app.secret_key = '123456'

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



