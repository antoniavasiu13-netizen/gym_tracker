from flask import Flask, render_template, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "secret_gym_key" # Required for sessions

@app.route('/')
def dashboard():
    session['last_page'] = 'Dashboard'
    return render_template('dashboard.html')

@app.route('/log', methods=['GET', 'POST'])
def log_workout():
    session['last_page'] = 'Log Workout'
    return render_template('log.html')

@app.route('/library')
def library():
    session['last_page'] = 'Exercise Library'
    return render_template('library.html')

@app.route('/timer')
def timer():
    session['last_page'] = 'Rest Timer'
    return render_template('timer.html')

@app.route('/settings')
def settings():
    session['last_page'] = 'Settings'
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)