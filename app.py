from flask import Flask, request, jsonify, render_template_string
from ultralytics import YOLO
import cv2
import mysql.connector
import os

app = Flask(__name__)

# =========================
# YOLO MODEL
# =========================

model = YOLO("yolov8n.pt")


# =========================
# MYSQL CONNECTION
# =========================

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="YOUR_MYSQL_PASSWORD",
    database="campus_detection"
)

cursor = db.cursor()


# =========================
# CREATE TABLE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    object_name VARCHAR(50),
    confidence FLOAT,
    severity VARCHAR(20),
    location VARCHAR(100),
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()


# =========================
# UPLOAD FOLDER
# =========================

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# =========================
# SEVERITY CALCULATION
# =========================

def calculate_severity(object_name, count):

    if object_name == "person":

        if count >= 20:
            return "HIGH"

        elif count >= 10:
            return "MEDIUM"

        else:
            return "LOW"

    elif object_name in [
        "car",
        "bus",
        "truck",
        "motorcycle"
    ]:

        if count >= 10:
            return "HIGH"

        elif count >= 5:
            return "MEDIUM"

        else:
            return "LOW"

    return "LOW"


# =========================
# SAVE TO MYSQL
# =========================

def save_detection(
    object_name,
    confidence,
    severity,
    location
):

    sql = """
    INSERT INTO detections
    (object_name, confidence, severity, location)
    VALUES (%s, %s, %s, %s)
    """

    values = (
        object_name,
        confidence,
        severity,
        location
    )

    cursor.execute(sql, values)
    db.commit()


# =========================
# HTML DASHBOARD
# =========================

HTML = """

<!DOCTYPE html>

<html>

<head>

<title>AI Smart Campus Detection</title>

<style>

body {
    font-family: Arial, sans-serif;
    background: #eef2f7;
    margin: 0;
    padding: 30px;
}

.container {
    max-width: 1000px;
    margin: auto;
    background: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.1);
}

h1 {
    text-align: center;
    color: #1e3a8a;
}

.upload {
    padding: 20px;
    background: #f8fafc;
    border-radius: 10px;
    margin-bottom: 25px;
}

input {
    padding: 10px;
    margin: 5px;
}

button {
    padding: 10px 20px;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

button:hover {
    background: #1d4ed8;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}

th {
    background: #1e3a8a;
    color: white;
}

th, td {
    padding: 12px;
    border-bottom: 1px solid #ddd;
    text-align: center;
}

.HIGH {
    color: red;
    font-weight: bold;
}

.MEDIUM {
    color: orange;
    font-weight: bold;
}

.LOW {
    color: green;
    font-weight: bold;
}

#result {
    margin-top: 20px;
    padding: 15px;
    background: #f1f5f9;
    border-radius: 10px;
}

</style>

</head>


<body>

<div class="container">

<h1>
🏫 AI SMART CAMPUS DETECTION
</h1>


<div class="upload">

<h3>
Upload Campus Image
</h3>


<form id="uploadForm">

<input
    type="file"
    name="image"
    accept="image/*"
    required
>

<input
    type="text"
    name="location"
    placeholder="Campus Location"
    value="Main Campus"
>

<button type="submit">
🔍 Detect
</button>

</form>

</div>


<div id="result">

<h3>
Detection Results
</h3>

<p>
Upload an image to start detection.
</p>

</div>


<h2>
🚨 Recent Campus Alerts
</h2>


<table>

<thead>

<tr>

<th>Object</th>
<th>Confidence</th>
<th>Severity</th>
<th>Location</th>
<th>Time</th>

</tr>

</thead>


<tbody id="alerts">

</tbody>

</table>


</div>


<script>


// ========================
// IMAGE DETECTION
// ========================

document
.getElementById("uploadForm")
.addEventListener("submit", async function(event) {

    event.preventDefault();

    const formData = new FormData(this);

    try {

        const response = await fetch(
            "/detect",
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        if (data.error) {

            document.getElementById("result").innerHTML =
                "<h3>Error</h3><p>" + data.error + "</p>";

            return;
        }

        let resultHTML = "";

        if (data.detections.length === 0) {

            resultHTML =
                "<p>No objects detected.</p>";

        }

        data.detections.forEach(item => {

            resultHTML += `

                <p>

                    <b>${item.object}</b>

                    &nbsp;&nbsp;

                    Count:
                    ${item.count}

                    &nbsp;&nbsp;

                    Confidence:
                    ${item.confidence}%

                    &nbsp;&nbsp;

                    <span class="${item.severity}">
                        ${item.severity}
                    </span>

                </p>

            `;

        });


        document.getElementById("result").innerHTML =
            "<h3>Detection Results</h3>"
            + resultHTML;


        loadAlerts();

    }

    catch (error) {

        document.getElementById("result").innerHTML =
            "<p>Detection failed.</p>";

        console.error(error);

    }

});


// ========================
// LOAD MYSQL ALERTS
// ========================

async function loadAlerts() {

    try {

        const response =
            await fetch("/api/detections");

        const data =
            await response.json();

        let html = "";


        data.forEach(item => {

            html += `

                <tr>

                    <td>
                        ${item.object}
                    </td>

                    <td>
                        ${item.confidence}%
                    </td>

                    <td class="${item.severity}">
                        ${item.severity}
                    </td>

                    <td>
                        ${item.location}
                    </td>

                    <td>
                        ${item.time}
                    </td>

                </tr>

            `;

        });


        document.getElementById("alerts").innerHTML =
            html;

    }

    catch (error) {

        console.error(
            "Failed to load alerts:",
            error
        );

    }

}


// Load alerts when page opens

loadAlerts();


</script>


</body>

</html>

"""


# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():

    return render_template_string(HTML)


# =========================
# DETECTION API
# =========================

@app.route("/detect", methods=["POST"])
def detect():

    # Check image

    if "image" not in request.files:

        return jsonify({
            "error": "No image uploaded"
        })


    file = request.files["image"]


    if file.filename == "":

        return jsonify({
            "error": "Please select an image"
        })


    # ========================
    # SAVE IMAGE
    # ========================

    filename = file.filename

    filepath = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    file.save(filepath)


    # ========================
    # READ IMAGE
    # ========================

    image = cv2.imread(filepath)


    if image is None:

        return jsonify({
            "error": "Invalid image"
        })


    # ========================
    # LOCATION
    # ========================

    location = request.form.get(
        "location",
        "Main Campus"
    )


    # ========================
    # YOLO DETECTION
    # ========================

    results = model(image)

    result = results[0]

    # ========================
    # COUNT OBJECTS + CONFIDENCE
    # ========================

    counts = {}
    confidence_totals = {}

    for box in result.boxes:

        class_id = int(box.cls[0])
        object_name = model.names[class_id]
        confidence = float(box.conf[0])

        counts[object_name] = counts.get(object_name, 0) + 1

        confidence_totals[object_name] = (
            confidence_totals.get(object_name, 0) + confidence
        )


    # ========================
    # BUILD DETECTIONS + SAVE TO DB
    # ========================

    detections = []

    for object_name, count in counts.items():

        avg_confidence = round(
            (confidence_totals[object_name] / count) * 100,
            2
        )

        severity = calculate_severity(object_name, count)

        save_detection(
            object_name,
            avg_confidence,
            severity,
            location
        )

        detections.append({
            "object": object_name,
            "count": count,
            "confidence": avg_confidence,
            "severity": severity
        })


    return jsonify({
        "detections": detections
    })


# =========================
# GET RECENT DETECTIONS (FOR DASHBOARD)
# =========================

@app.route("/api/detections", methods=["GET"])
def get_detections():

    query = """
    SELECT object_name, confidence, severity, location, detected_at
    FROM detections
    ORDER BY detected_at DESC
    LIMIT 20
    """

    cursor.execute(query)

    rows = cursor.fetchall()

    detections = []

    for row in rows:

        detections.append({
            "object": row[0],
            "confidence": row[1],
            "severity": row[2],
            "location": row[3],
            "time": row[4].strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify(detections)


# =========================
# RUN APP
# =========================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
