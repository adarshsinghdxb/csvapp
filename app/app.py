import os
import csv
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "csvapp-secret-key")

# Local storage directory (simulates S3 in local mode)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "processed")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

METADATA_FILE = os.path.join(UPLOAD_FOLDER, "metadata.json")


def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return []


def save_metadata(metadata):
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f)


def parse_csv(file):
    rows = []
    content = file.read().decode("utf-8-sig")
    lines = content.splitlines()
    reader = csv.reader(lines)
    for row in reader:
        if len(row) == 3:
            rows.append({
                "product_id": row[0].strip().strip('"'),
                "product_name": row[1].strip().strip('"'),
                "price": float(row[2].strip().strip('"'))
            })
    return rows


@app.route("/", methods=["GET"])
def index():
    processed_files = load_metadata()
    return render_template("index.html", processed_files=processed_files)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("No file selected", "error")
        return redirect(url_for("index"))

    file = request.files["file"]

    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("index"))

    if not file.filename.endswith(".csv"):
        flash("Only CSV files allowed", "error")
        return redirect(url_for("index"))

    rows = parse_csv(file)

    # Save file locally (simulates S3 upload)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{timestamp}_{file.filename}"
    saved_path = os.path.join(UPLOAD_FOLDER, saved_filename)

    with open(saved_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Product ID", "Product Name", "Price"])
        for row in rows:
            writer.writerow([row["product_id"], row["product_name"], row["price"]])

    # Update metadata
    metadata = load_metadata()
    metadata.append({
        "filename": file.filename,
        "saved_as": saved_filename,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "row_count": len(rows)
    })
    save_metadata(metadata)

    return render_template("result.html", rows=rows, filename=file.filename)


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
