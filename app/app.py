import os
import csv
import json
import boto3
from datetime import datetime
from botocore.exceptions import NoCredentialsError
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "csvapp-secret-key")

# S3 config - reads from environment variables
S3_BUCKET = os.environ.get("S3_BUCKET", "csvapp-processed-files")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")

# Local fallback folder
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


def upload_to_s3(local_path, s3_key):
    try:
        s3 = boto3.client("s3", region_name=S3_REGION)
        s3.upload_file(local_path, S3_BUCKET, f"processed/{s3_key}")
        print(f"Uploaded to S3: {s3_key}")
        return True
    except NoCredentialsError:
        print("No AWS credentials found, skipping S3 upload")
        return False
    except Exception as e:
        print(f"S3 upload failed: {e}")
        return False


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

    # Save locally first
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{timestamp}_{file.filename}"
    saved_path = os.path.join(UPLOAD_FOLDER, saved_filename)

    with open(saved_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Product ID", "Product Name", "Price"])
        for row in rows:
            writer.writerow([row["product_id"], row["product_name"], row["price"]])

    # Upload to S3
    s3_uploaded = upload_to_s3(saved_path, saved_filename)

    # Update metadata
    metadata = load_metadata()
    metadata.append({
        "filename": file.filename,
        "saved_as": saved_filename,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "row_count": len(rows),
        "s3_uploaded": s3_uploaded
    })
    save_metadata(metadata)

    return render_template("result.html", rows=rows, filename=file.filename, s3_uploaded=s3_uploaded)


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)