import os
import pandas as pd
import csv
from flask import Flask, render_template, request, jsonify, send_file
from fetchSolarIrradiance import fetchSolarIrradiance
from calculateEnergyOutput import calculate_energy_output_prediction

app = Flask(__name__)

coords_file = os.path.join(os.getcwd(), 'coords.txt')

#main page
@app.route('/')
def index():
    # TH - หน้า index ที่ให้กรอก city กับ country
    # EN - Index page where you enter city and country.
    return render_template('index.html')

#Route for getting latitude and lonitude by input city and country name
@app.route('/predict', methods=['POST'])
def predict_location():
    data = request.get_json()
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])
    start = data['start_datetime']
    end = data['end_datetime']

    if latitude is None or longitude is None:
        return jsonify({"error": "Latitude and longitude are required"}), 400

    with open(coords_file, 'w') as file:
        file.write(f"Latitude: {latitude}, Longitude: {longitude}\n")

    fetchSolarIrradiance(latitude, longitude, start, end)
    hourly_predictions = calculate_energy_output_prediction()

    # Ensure the directory exists
    os.makedirs(os.path.join('data'), exist_ok=True)
    # Save predictions to HourOrderAndEstimated.csv 
    output_path = os.path.join('data', 'HourOrderAndEstimated.csv')
    with open(output_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Hour', 'Estimated Energy'])  # kWh
        for hour, value in enumerate(hourly_predictions, start=1):
            writer.writerow([hour, round(value, 4)])

    return jsonify({"message": "Prediction completed successfully."}), 200

#Route for getting latitude and lonitude by manual
# Entering Location manually linked to /location.html

@app.route('/location', methods=['GET', 'POST'])
def enter_location():
    if request.method == 'POST':
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        # Error preventing empty input.
        if not latitude or not longitude:
            return render_template(
                'location.html',
                error="Please enter both latitude and longitude.",
                latitude=latitude,
                longitude=longitude
            )
        # Error preventing out of range input.
        elif not (-90 <= int(latitude) <= 90) or not (-180 <= int(longitude) <= 180):
            return render_template(
                'location.html',
                error="Please input number between -90 to 90 for latitude and -180 to 180 for longitude."
            )

        coords_message = f"Latitude: {latitude}, Longitude: {longitude}\n"
        with open(coords_file, 'w') as file:
            file.write(coords_message)

        return render_template(
            'location.html',
            success="Coordinates saved successfully!",
            latitude_display=latitude,
            longitude_display=longitude
        )

    # TH - Method GET — ลองอ่าน coords.txt ถ้ามี
    # EN - Method GET — Try to read coords.txt if there is one.
    lat, lon = None, None
    if os.path.exists(coords_file):
        with open(coords_file, 'r') as file:
            content = file.read().strip()
            try:

                # TH - แยกพิกัดจากข้อความในไฟล์
                # EN - Separate cords. from text in file.

                parts = content.replace("Latitude: ", "").replace("Longitude: ", "").split(',')
                lat = parts[0].strip()
                lon = parts[1].strip()
            except IndexError:
                pass  # TH - ถ้าอ่านไม่ได้ก็ไม่ต้องแสดง EN - Won't display if cannot read file.

    return render_template('location.html', latitude=lat, longitude=lon)

# Route to handle PV system configuration
@app.route('/submit_pv', methods=['POST'])
def submit_pv():
    data = request.get_json()

    area = data.get('area')
    panel_eff = data.get('panel_efficiency')
    inverter_eff = data.get('inverter_efficiency')

    # Write PV system configuration to file
    with open('pv_config.txt', 'w', encoding='utf-8') as f:
        f.write(f"Panel Area: {area}\n")
        f.write(f"Panel Efficiency: {panel_eff}\n")
        f.write(f"Inverter Efficiency: {inverter_eff}\n")

    return jsonify({"message": "PV system configuration saved successfully."})

#Check if pv_config.txt exists
@app.route('/check_pv_config')
def check_pv_config():
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pv_config.txt')
    exists = os.path.exists(file_path)
    return jsonify({'exists': exists})  

#Power Prediction Table
@app.route('/energy_data', methods=['GET'])
def get_energy_data():
    data = []
    try:
        file_path = os.path.join('data', 'HourOrderAndEstimated.csv')
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            data.append({
                'Hour': int(row['Hour']),
                'Estimated_Energy': float(row['Estimated Energy'])
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(data)

#Send HourOrderAndEstimated.csv to front end
@app.route('/data/HourOrderAndEstimated.csv')
def serve_estimated_csv():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'data', 'HourOrderAndEstimated.csv')
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            f.write('Hour,Estimated Energy\n')
    return send_file(file_path, mimetype='text/csv')

@app.route('/data/solar_radiation_data.csv')
def serve_radiation_csv():
    file_path = os.path.join('data', 'solar_radiation_data.csv')
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            f.write('timestamp,solar_radiation\n')
    return send_file(file_path, mimetype='text/csv')

#Show the Total in the table
@app.route('/results')
def show_results():
    try:
        file_path = os.path.join('data', 'HourOrderAndEstimated.csv')

        df = pd.read_csv(file_path)

        df['Estimated Energy (kWh)'] = df['Estimated Energy'] 

        energy_data = df[['Hour', 'Estimated Energy (kWh)']].to_dict(orient='records')
        total_energy = df['Estimated Energy (kWh)'].sum()
    except Exception as e:
        return render_template('error.html', message=str(e))

    return render_template('results.html', energy_data=energy_data, total_energy=round(total_energy, 2))

if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)
