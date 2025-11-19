"""
Flask application for the web UI.
"""
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import json
import time
from dotenv import load_dotenv
from config import FLASK_SECRET_KEY, MAX_CONTENT_LENGTH, UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from tasks import process_csv_import, bulk_delete_products
from celery.result import AsyncResult
from celery_app import celery_app
import os

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
CORS(app)

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    """Main page."""
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """
    Handle file upload and start async processing.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only CSV files are allowed."}), 400
    
    try:
        # Read file content
        file_content = file.read().decode("utf-8")
        
        # Start async task
        task = process_csv_import.delay(file_content, file.filename)
        
        return jsonify({
            "task_id": task.id,
            "status": "processing",
            "message": "File upload started. Processing in background..."
        }), 202
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/task/<task_id>/status")
def get_task_status(task_id):
    """
    Get status of a Celery task.
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result.state == "PENDING":
            response = {
                "state": task_result.state,
                "progress": 0,
                "status": "pending",
                "message": "Task is waiting to be processed..."
            }
        elif task_result.state == "PROGRESS":
            meta = task_result.info or {}
            response = {
                "state": task_result.state,
                "progress": meta.get("progress", 0),
                "status": meta.get("status", "processing"),
                "message": meta.get("message", "Processing...")
            }
        elif task_result.state == "SUCCESS":
            result = task_result.result
            response = {
                "state": task_result.state,
                "progress": 100,
                "status": "complete",
                "message": "Import completed successfully!",
                "result": result
            }
        else:
            # FAILURE or other states
            response = {
                "state": task_result.state,
                "progress": 0,
                "status": "error",
                "message": str(task_result.info) if task_result.info else "Task failed",
                "error": str(task_result.info) if task_result.info else "Unknown error"
            }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/task/<task_id>/stream")
def stream_task_status(task_id):
    """
    Server-Sent Events stream for real-time task progress.
    """
    def generate():
        """Generate SSE events."""
        while True:
            try:
                task_result = AsyncResult(task_id, app=celery_app)
                
                if task_result.state == "PENDING":
                    data = {
                        "state": task_result.state,
                        "progress": 0,
                        "status": "pending",
                        "message": "Task is waiting to be processed..."
                    }
                elif task_result.state == "PROGRESS":
                    meta = task_result.info or {}
                    data = {
                        "state": task_result.state,
                        "progress": meta.get("progress", 0),
                        "status": meta.get("status", "processing"),
                        "message": meta.get("message", "Processing...")
                    }
                elif task_result.state == "SUCCESS":
                    result = task_result.result
                    data = {
                        "state": task_result.state,
                        "progress": 100,
                        "status": "complete",
                        "message": "Import completed successfully!",
                        "result": result
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    break
                else:
                    # FAILURE
                    data = {
                        "state": task_result.state,
                        "progress": 0,
                        "status": "error",
                        "message": str(task_result.info) if task_result.info else "Task failed",
                        "error": str(task_result.info) if task_result.info else "Unknown error"
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    break
                
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(0.5)  # Poll every 500ms
                
            except Exception as e:
                error_data = {
                    "state": "ERROR",
                    "progress": 0,
                    "status": "error",
                    "message": str(e),
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                break
    
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


if __name__ == "__main__":
    from config import FLASK_HOST, FLASK_PORT
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)

