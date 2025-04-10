from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import json
from datetime import datetime
from scheduler import Program, TimeSlot, Scheduler, create_weekly_time_slots

app = Flask(__name__)

# 数据库设置
def get_db_connection():
    conn = sqlite3.connect('rehearsal.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS programs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        week_start TEXT NOT NULL
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS preferred_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        program_id INTEGER,
        day TEXT NOT NULL,
        start_hour INTEGER NOT NULL,
        end_hour INTEGER NOT NULL,
        FOREIGN KEY (program_id) REFERENCES programs (id)
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_start TEXT NOT NULL,
        schedule_data TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/programs', methods=['GET'])
def get_programs():
    conn = get_db_connection()
    programs = conn.execute('SELECT * FROM programs ORDER BY id DESC').fetchall()
    conn.close()
    
    result = []
    for program in programs:
        conn = get_db_connection()
        slots = conn.execute('SELECT * FROM preferred_slots WHERE program_id = ?', 
                            (program['id'],)).fetchall()
        conn.close()
        
        program_data = dict(program)
        program_data['preferred_slots'] = [dict(slot) for slot in slots]
        result.append(program_data)
    
    return jsonify(result)

@app.route('/programs', methods=['POST'])
def add_program():
    data = request.json
    name = data.get('name')
    week_start = data.get('week_start', datetime.now().strftime('%Y-%m-%d'))
    preferred_slots = data.get('preferred_slots', [])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO programs (name, week_start) VALUES (?, ?)',
                  (name, week_start))
    program_id = cursor.lastrowid
    
    for slot in preferred_slots:
        cursor.execute('''
        INSERT INTO preferred_slots (program_id, day, start_hour, end_hour)
        VALUES (?, ?, ?, ?)
        ''', (program_id, slot['day'], slot['start_hour'], slot['end_hour']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'id': program_id, 'name': name, 'week_start': week_start})

@app.route('/generate_schedule', methods=['POST'])
def generate_schedule():
    data = request.json
    week_start = data.get('week_start', datetime.now().strftime('%Y-%m-%d'))
    
    # 获取该周的所有节目
    conn = get_db_connection()
    programs_data = conn.execute('''
    SELECT * FROM programs WHERE week_start = ?
    ''', (week_start,)).fetchall()
    
    programs = []
    for p_data in programs_data:
        slots_data = conn.execute('''
        SELECT * FROM preferred_slots WHERE program_id = ?
        ''', (p_data['id'],)).fetchall()
        
        preferred_slots = []
        for slot in slots_data:
            preferred_slots.append(
                TimeSlot(slot['day'], slot['start_hour'], slot['end_hour'])
            )
        
        programs.append(Program(p_data['id'], p_data['name'], preferred_slots))
    
    # 生成时间表
    time_slots = create_weekly_time_slots()
    scheduler = Scheduler(time_slots, programs)
    schedule = scheduler.allocate()
    
    # 准备结果
    result = {
        'assignments': {},
        'program_assignments': {}
    }
    
    # 按时间段排序
    for slot, venues in schedule.assignments.items():
        slot_str = f"{slot.day} {slot.start_hour}:00-{slot.end_hour}:00"
        result['assignments'][slot_str] = {}
        
        for venue, program in venues.items():
            result['assignments'][slot_str][venue] = {
                'id': program.id,
                'name': program.name
            }
    
    # 按节目排序
    for program in programs:
        if program.assigned_slots:
            result['program_assignments'][program.name] = []
            for slot, venue in program.assigned_slots:
                slot_str = f"{slot.day} {slot.start_hour}:00-{slot.end_hour}:00"
                result['program_assignments'][program.name].append({
                    'slot': slot_str,
                    'venue': venue
                })
    
    # 保存到数据库
    conn.execute('''
    INSERT INTO schedules (week_start, schedule_data, created_at)
    VALUES (?, ?, ?)
    ''', (week_start, json.dumps(result), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    conn.commit()
    conn.close()
    
    return jsonify(result)

@app.route('/schedules', methods=['GET'])
def get_schedules():
    conn = get_db_connection()
    schedules = conn.execute('SELECT * FROM schedules ORDER BY created_at DESC').fetchall()
    conn.close()
    
    result = []
    for schedule in schedules:
        result.append({
            'id': schedule['id'],
            'week_start': schedule['week_start'],
            'created_at': schedule['created_at'],
            'data': json.loads(schedule['schedule_data'])
        })
    
    return jsonify(result)

@app.route('/schedules/<int:schedule_id>', methods=['GET'])
def get_schedule(schedule_id):
    conn = get_db_connection()
    schedule = conn.execute('SELECT * FROM schedules WHERE id = ?', 
                           (schedule_id,)).fetchone()
    conn.close()
    
    if schedule:
        return jsonify({
            'id': schedule['id'],
            'week_start': schedule['week_start'],
            'created_at': schedule['created_at'],
            'data': json.loads(schedule['schedule_data'])
        })
    else:
        return jsonify({'error': 'Schedule not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 