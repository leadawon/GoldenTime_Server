from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, Users, Station, Plug, Plug_Raw, Storage
import requests
from datetime import datetime
from dateutil import parser
DEVICE_ID = "29e137c3-04b5-44f2-8689-5e33fc555a60"
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/initdb')
def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
    return "Database initialized!"

@app.route('/create_test_data')
def create_test_data():
    with app.app_context():
        new_user = Users(name="test_user")
        new_user.set_password("password")
        db.session.add(new_user)
        db.session.commit()

        new_station = Station(user_id=new_user.id)
        db.session.add(new_station)
        db.session.commit()

        new_plug = Plug(station_id=new_station.id, device_id="29e137c3-04b5-44f2-8689-5e33fc555a60", device_type="godegee")
        db.session.add(new_plug)
        db.session.commit()
        
        # 새로운 세션을 통해 데이터 조회
        user_id = new_user.id
        station_id = new_station.id
        plug_id = new_plug.id

    return jsonify({
        "user_id": user_id,
        "station_id": station_id,
        "plug_id": plug_id
    })

@app.route('/create_plug', methods=['POST'])
def create_plug():
    data = request.get_json()
    station_id = data.get('station_id')
    device_id = data.get('device_id')
    device_type = data.get('device_type')
    
    with app.app_context():
        # station_id가 존재하는지 확인
        station = Station.query.get(station_id)
        if not station:
            return jsonify({"error": "Station not found"}), 404

        # 새로운 플러그 생성 및 추가
        new_plug = Plug(station_id=station_id, device_id=device_id, device_type=device_type)
        db.session.add(new_plug)
        db.session.commit()
        
        return jsonify({
            "station_id": new_plug.station_id,
            "plug_id": new_plug.id,
            "device_id": new_plug.device_id,
            "device_type": new_plug.device_type
        })

@app.route('/golden_test/<int:plug_id>')
def golden_test(plug_id):
    with app.app_context():
        plug = Plug.query.get(plug_id)
        if plug:
            data, _ = fetch_data(plug.id, plug.device_id)
            components = data.get('components', {}).get('main', {})
            switch_info = components.get('switch', {}).get('switch', {})
            
            if switch_info.get('value', 'off') == 'on':
                start_date_str = switch_info.get('timestamp', datetime.utcnow().isoformat())
                start_date = parser.parse(start_date_str).replace(tzinfo=None)  # offset-naive로 변환
                current_date = datetime.utcnow()
                time_difference = (current_date - start_date).total_seconds() / 60  # 분 단위로 변환
                if time_difference > plug.golden_time:
                    return jsonify({"status": True, "reason": "Time threshold exceeded"})
            
            power_info = components.get('powerMeter', {}).get('power', {})
            power_value = power_info.get('value', 0.0)
            if power_value > plug.golden_power:
                return jsonify({"status": True, "reason": "Power threshold exceeded"})
            
            return jsonify({"status": False})
        else:
            return "No plug found!"

@app.route('/golden_test/all')
def golden_test_all():
    with app.app_context():
        plugs = Plug.query.all()
        results = []
        for plug in plugs:
            data, _ = fetch_data(plug.id, plug.device_id)
            components = data.get('components', {}).get('main', {})
            switch_info = components.get('switch', {}).get('switch', {})
            
            if switch_info.get('value', 'off') == 'on':
                start_date_str = switch_info.get('timestamp', datetime.utcnow().isoformat())
                start_date = parser.parse(start_date_str).replace(tzinfo=None)  # offset-naive로 변환
                current_date = datetime.utcnow()
                time_difference = (current_date - start_date).total_seconds() / 60  # 분 단위로 변환
                if time_difference > plug.golden_time:
                    results.append({
                        "plug_id": plug.id,
                        "status": True,
                        "reason": "Time threshold exceeded"
                    })
                    continue
            
            power_info = components.get('powerMeter', {}).get('power', {})
            power_value = power_info.get('value', 0.0)
            if power_value > plug.golden_power:
                results.append({
                    "plug_id": plug.id,
                    "status": True,
                    "reason": "Power threshold exceeded"
                })
                continue
            
            results.append({
                "plug_id": plug.id,
                "status": False,
                "reason": None
            })
        
        return jsonify(results)


@app.route('/read_plugs', methods=['GET'])
def read_plugs():
    with app.app_context():
        plugs = Plug.query.all()
        result = []
        for plug in plugs:
            
            data, _ = fetch_data(plug.id, plug.device_id)
            components = data.get('components', {}).get('main', {})

            power_info = components.get('powerMeter', {}).get('power', {})
            power_value = power_info.get('value', 0.0)

            power_consumption_info = components.get('powerConsumptionReport', {}).get('powerConsumption', {}).get('value', {})
            total_energy = power_consumption_info.get('energy', 0)

            switch_info = components.get('switch', {}).get('switch', {})
            switch_value = switch_info.get('value', 'off')
            start_date_str = switch_info.get('timestamp', datetime.utcnow().isoformat())

            power_state = switch_value
            current_date = datetime.utcnow()

            # 문자열을 datetime 객체로 변환
            start_date = parser.parse(start_date_str)

                
            result.append({
                "plug_id": plug.id,
                "device_id": plug.device_id,
                "power_state": power_state,
                "current_power": power_value,
                "total_power_usage": total_energy,
                "current_date": current_date.isoformat(),
                "start_date": start_date.isoformat()
            })

        return jsonify(result)

## ------------------------- ##

# 토큰을 파일에서 읽어오는 함수
def get_api_token():
    with open('private/samsungtoken.txt', 'r') as file:
        return file.read().strip()





# 개별 플러그의 데이터를 가져오는 함수
def fetch_data(plug_id, device_id):
    headers = {
        "Authorization": f"Bearer {get_api_token()}"
    }
    try:
        response = requests.get(f"https://api.smartthings.com/v1/devices/{device_id}/status", headers=headers)
        response.raise_for_status()
        data = response.json()
        return data, plug_id
    except requests.exceptions.RequestException as e:
        print(f"HTTP request failed: {e}")

# 데이터를 데이터베이스에 저장하는 함수
def store_data(data, plug_id):
    with app.app_context():
        components = data.get('components', {}).get('main', {})

        power_info = components.get('powerMeter', {}).get('power', {})
        power_value = power_info.get('value', 0.0)

        power_consumption_info = components.get('powerConsumptionReport', {}).get('powerConsumption', {}).get('value', {})
        total_energy = power_consumption_info.get('energy', 0)

        switch_info = components.get('switch', {}).get('switch', {})
        switch_value = switch_info.get('value', 'off')
        start_date_str = switch_info.get('timestamp', datetime.utcnow().isoformat())

        power_state = switch_value
        current_date = datetime.utcnow()

        # 문자열을 datetime 객체로 변환
        start_date = parser.parse(start_date_str)

        new_plug_raw = Plug_Raw(
            plug_id=plug_id,
            power_state=power_state,
            current_power=power_value,
            total_power_usage=total_energy,
            current_date=current_date,
            start_date=start_date,
        )

        db.session.add(new_plug_raw)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Failed to add data to database: {e}")

# 모든 플러그의 데이터를 가져오는 함수

def fetch_all_plugs_data():
    with app.app_context():
        #print("fetch scheduler working!")
        plugs = Plug.query.all()
        for plug in plugs:
            data, plug_id = fetch_data(plug.id, plug.device_id)
            store_data(data, plug_id)



if __name__ == '__main__':
    with app.app_context():
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=fetch_all_plugs_data, trigger="interval", minutes=1)
        scheduler.start()

        try:
            app.run(debug=True)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()