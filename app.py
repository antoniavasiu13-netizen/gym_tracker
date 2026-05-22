import json
import os
import urllib.request
from datetime import datetime, date, timedelta

from flask import Flask, render_template, session, redirect, url_for, request

app = Flask(__name__)
app.secret_key = 'gym_tracker_super_secret_key' 

# Home route
@app.route('/', methods=['GET', 'POST'])
def home():
    if 'theme' not in session:
        session['theme'] = 'light'
        
    if 'username' in session:
        return redirect(url_for('dashboard')) 
        
    # Create a dictionary in session storage if it doesn't exist yet
    if 'registered_accounts' not in session:
        session['registered_accounts'] = {}
        
    error_message = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        remember = request.form.get('remember_me')
        password = request.form.get('password')

        if username and password:
            accounts = session['registered_accounts']
            
            # For new user save whatever password they typed
            if username not in accounts:
                accounts[username] = password
                session['registered_accounts'] = accounts
                session.modified = True  # Tell Flask to save the data update
                
            # For existing user check if the password matches their first password
            if accounts[username] == password:
                session['username'] = username
                if remember:
                    session['remember_me'] = True
                    session.permanent = True 
                else:
                    session['remember_me'] = False
                    session.permanent = False
                return redirect(url_for('dashboard'))
            else:
                # Error message for wrong password
                error_message = "Incorrect password for this username."
            
    return render_template('home.html', error=error_message)

# Dashboard route
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('home'))
        
    current_user = session['username']
    
    if 'profiles_data' not in session:
        session['profiles_data'] = {}
    if 'users_data' not in session:
        session['users_data'] = {}
        
    profiles_data = session['profiles_data']
    users_data = session['users_data']
    
    if request.method == 'POST':
        goal = request.form.get('goal')
        current_weight = request.form.get('current_weight')
        target_weight = request.form.get('target_weight')
    
        user_data = profiles_data.get(current_user, {
            'goal': '', 'current_weight': '', 'target_weight': ''
        })
        user_data['goal'] = goal
        user_data['current_weight'] = current_weight
        user_data['target_weight'] = target_weight
        
        profiles_data[current_user] = user_data
        session['profiles_data'] = profiles_data
        session.modified = True
        return redirect(url_for('dashboard'))

    user_goals = profiles_data.get(current_user, {
        'goal': '', 'current_weight': '', 'target_weight': ''
    })

    user_history = users_data.get(current_user, [])

    # Create real time streak and calendar for storing data
    calculated_streak = 0
    workout_dates = set()
    all_logged_dates = [] 
    
    for entry in user_history:
        date_str = entry.get('date', '')
        if date_str:
            all_logged_dates.append(date_str)
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d').date()
                workout_dates.add(dt)
            except ValueError:
                continue

    if workout_dates:
        today_date = date.today()
        yesterday_date = today_date - timedelta(days=1)
        
        if today_date in workout_dates or yesterday_date in workout_dates:
            check_date = today_date if today_date in workout_dates else yesterday_date
            while check_date in workout_dates:
                calculated_streak += 1
                check_date -= timedelta(days=1) 

    user_goals['streak'] = calculated_streak

    # Define rewarding scores depending on the frequency of gym attendance
    weekly_counts = {}
    for entry in user_history:
        date_str = entry.get('date', '')
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                week_number = date_obj.strftime('%U') 
                week_label = f"Wk {week_number}"
                weekly_counts[week_label] = weekly_counts.get(week_label, 0) + 1
            except ValueError:
                continue

    sorted_weeks = sorted(weekly_counts.keys())
    graph_labels = []
    graph_data = []
    
    for week in sorted_weeks:
        workouts_this_week = weekly_counts[week]
        graph_labels.append(week)
        
        if workouts_this_week >= 6:
            graph_data.append(20)
        elif workouts_this_week >= 4:
            graph_data.append(15)
        elif workouts_this_week == 3:
            graph_data.append(10)
        elif workouts_this_week >= 1:
            graph_data.append(5)
        else:
            graph_data.append(0)

    if not graph_labels or graph_labels == ['No Entries']:
        graph_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        graph_data = [5, 10, 15, 20]

    # Weather API
    weather_temp = ""
    weather_desc = ""
    weather_icon = ""
    gym_recommendation = ""

    try:
        import ssl
        ssl_context = ssl._create_unverified_context()
        
        url = "https://wttr.in/Kolding?format=j1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=3, context=ssl_context) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                current = data.get('current_condition', [{}])[0]
                
                # Get the temperature and description text directly
                weather_temp = f"{current.get('temp_C', '--')}°C"
                desc = current.get('weatherDesc', [{}])[0].get('value', '').lower()
                weather_desc = desc.capitalize()
                
                # Dynamic icon checkers based on conditions
                if any(word in desc for word in ['rain', 'shower', 'storm', 'drizzle', 'sleet', 'snow', 'mist', 'fog']):
                    weather_icon = "fa-cloud-showers-heavy"
                    gym_recommendation = "Bad weather outside! Perfect day for a heavy indoor gym session."
                    
                elif any(word in desc for word in ['clear', 'sunny', 'fair']):
                    weather_icon = "fa-sun"
                    gym_recommendation = "Beautiful day! Consider a warm-up run outside before your lift."
                    
                else:
                    weather_icon = "fa-cloud"
                    gym_recommendation = "Great day to work on your goals. Let's get a session in!"
                    
    except Exception:
        # Fallback error text if offline
        weather_temp = "--°C"
        weather_desc = "Offline"
        weather_icon = "fa-triangle-exclamation"
        gym_recommendation = "Weather feed is currently unavailable."

    return render_template(
        'dashboard.html', 
        user_goals=user_goals, graph_labels=graph_labels, graph_data=graph_data,
        all_logged_dates=all_logged_dates,
        weather_temp=weather_temp, weather_desc=weather_desc, weather_icon=weather_icon,
        gym_recommendation=gym_recommendation
    )

# Light/Dark Mode
@app.route('/toggle-theme')
def toggle_theme():
    if session.get('theme') == 'dark':
        session['theme'] = 'light'
    else:
        session['theme'] = 'dark'
    return redirect(request.referrer or url_for('home'))

# User's history depending on the workout info
@app.route('/workout', methods=['GET', 'POST'])
def workout_info():
    session['last_page'] = 'Workout Info'
    if 'username' not in session:
        return redirect(url_for('home'))

    current_user = session['username']
    if 'users_data' not in session:
        session['users_data'] = {}

    users_data = session['users_data']
    if current_user not in users_data:
        users_data[current_user] = []

    user_history = users_data[current_user]

    #
    today_str = date.today().strftime('%Y-%m-%d')

    if request.method == 'POST':
        workout_date = request.form.get('workout_date')
        body_part = request.form.get('body_part')
        intensity = request.form.get('intensity')

        # Block following days, preventing the user from entering the wrong data
        if workout_date > today_str:
            return redirect(url_for('workout_info'))

        workout_entry = {
            'date': workout_date, 'body_part': body_part, 'intensity': intensity
        }
        user_history.append(workout_entry)
        users_data[current_user] = user_history
        session['users_data'] = users_data
        session.modified = True
        return redirect(url_for('workout_info'))

    return render_template('workout.html', personal_history=user_history, today_date=today_str)

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

# Workout library route
@app.route('/library')
def library():
    if 'username' not in session:
        return redirect(url_for('home'))
    json_path = os.path.join(app.root_path, 'data', 'exercises_mini.json')
    exercises = []
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            try: exercises = json.load(f)
            except json.JSONDecodeError: exercises = []
    return render_template('library.html', exercises=exercises)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
