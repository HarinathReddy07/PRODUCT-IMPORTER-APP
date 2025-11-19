# Product Importer - Acme Inc.

A scalable web application for importing and managing products from CSV files. Built with Flask (UI), FastAPI (API), Celery (async processing), and PostgreSQL.

## Features

### STORY 1 - File Upload via UI
- Upload large CSV files (up to 500,000 products, 500MB)
- Real-time progress tracking using Server-Sent Events (SSE)
- Automatic duplicate handling (case-insensitive SKU matching)
- Visual progress indicators with status messages

### STORY 2 - Product Management UI
- View, create, update, and delete products
- Filter by SKU, name, description, and active status
- Paginated product listing
- Inline editing with modal forms

### STORY 3 - Bulk Delete
- Delete all products with confirmation dialog
- Async processing with status tracking

### STORY 4 - Webhook Configuration
- Manage webhooks via UI
- Add, edit, delete, and test webhooks
- Support for multiple event types
- Visual confirmation of test triggers

## Tech Stack

- **Web Frameworks**: Flask (UI) + FastAPI (API)
- **Async Processing**: Celery with Redis
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL
- **Frontend**: Vanilla JavaScript with modern CSS

## Project Structure

```
.
├── api.py                 # FastAPI application (REST API)
├── flask_app.py          # Flask application (Web UI)
├── models.py             # SQLAlchemy models
├── tasks.py              # Celery async tasks
├── celery_app.py         # Celery configuration
├── webhook_utils.py      # Webhook utilities
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── templates/            # HTML templates
│   └── index.html
├── static/               # Static files
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── uploads/              # Upload directory (created automatically)
```

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis

#### Installing Redis on Windows

**Option 1: Using WSL (Recommended)**
```bash
# Install WSL (run PowerShell as Administrator)
wsl --install

# After restart, open Ubuntu/WSL and run:
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

**Option 2: Using Memurai (Windows-compatible Redis)**
1. Download from: https://www.memurai.com/get-memurai
2. Install and start the service
3. Redis will run on `localhost:6379`

**Option 3: Using Docker**
```bash
docker run -d -p 6379:6379 redis:latest
```

**Option 4: Use Cloud Redis (for development)**
- Use a free Redis service like Redis Cloud or Upstash
- Update `REDIS_URL` in `.env` with the cloud connection string

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Assignment
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy .env.example to .env and edit with your database and Redis credentials
   # Update DATABASE_URL with your PostgreSQL connection string
   ```

5. **Initialize database**
   ```bash
   python init_db.py
   ```

## Running the Application

**Prerequisites:** Make sure PostgreSQL and Redis are running before starting the applications.

**Open 4 separate terminal windows and run these commands:**

### Terminal 1 - Start Redis
```bash
redis-server
```

### Terminal 2 - Start Celery Worker
```bash
celery -A celery_app worker --loglevel=info
```

### Terminal 3 - Start Flask Application (UI)
```bash
python flask_app.py
```
Access UI at: `http://localhost:5000`

### Terminal 4 - Start FastAPI Application (API)
```bash
python api.py
```
Or:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```
API available at: `http://localhost:8000`

## Usage

### CSV File Format

The CSV file should have the following columns:
- `sku` (required): Product SKU (case-insensitive, unique)
- `name` (required): Product name
- `description` (optional): Product description

Example CSV:
```csv
sku,name,description
SKU001,Product 1,Description 1
SKU002,Product 2,Description 2
```

### API Endpoints

#### Products
- `GET /api/products` - List products (with pagination and filters)
- `GET /api/products/{id}` - Get product by ID
- `POST /api/products` - Create product
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product
- `POST /api/products/bulk-delete` - Delete all products (async)

#### Webhooks
- `GET /api/webhooks` - List all webhooks
- `GET /api/webhooks/{id}` - Get webhook by ID
- `POST /api/webhooks` - Create webhook
- `PUT /api/webhooks/{id}` - Update webhook
- `DELETE /api/webhooks/{id}` - Delete webhook
- `POST /api/webhooks/{id}/test` - Test webhook

#### Tasks
- `GET /api/tasks/{task_id}` - Get task status

### Webhook Events

The following events trigger webhooks:
- `product.created` - When a product is created
- `product.updated` - When a product is updated
- `product.deleted` - When a product is deleted
- `product.bulk_import` - When CSV import completes
- `product.bulk_delete` - When bulk delete completes

## Database Schema

### Products Table
- `id` (Integer, Primary Key)
- `sku` (String, Unique, Case-insensitive)
- `name` (String)
- `description` (Text, Nullable)
- `active` (Boolean, Default: True)
- `created_at` (DateTime)
- `updated_at` (DateTime)

### Webhooks Table
- `id` (Integer, Primary Key)
- `url` (String)
- `event_type` (String)
- `enabled` (Boolean, Default: True)
- `secret` (String, Nullable)
- `created_at` (DateTime)
- `updated_at` (DateTime)

## Deployment

### Environment Variables

Set the following environment variables in your deployment platform:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `CELERY_BROKER_URL`: Celery broker URL
- `CELERY_RESULT_BACKEND`: Celery result backend URL
- `FLASK_SECRET_KEY`: Secret key for Flask sessions
- `FLASK_HOST`: Flask host (default: 0.0.0.0)
- `FLASK_PORT`: Flask port (default: 5000)
- `FASTAPI_HOST`: FastAPI host (default: 0.0.0.0)
- `FASTAPI_PORT`: FastAPI port (default: 8000)

### Deployment Platforms

#### Heroku
1. Create `Procfile`:
   ```
   web: gunicorn flask_app:app
   api: uvicorn api:app --host 0.0.0.0 --port $PORT
   worker: celery -A celery_app worker --loglevel=info
   ```

2. Deploy using Heroku CLI

#### Render
1. Create separate services for:
   - Flask app
   - FastAPI app
   - Celery worker
   - Redis (managed service)
   - PostgreSQL (managed service)

#### Docker
Create `Dockerfile` and `docker-compose.yml` for containerized deployment.

## Performance Considerations

- CSV processing is done asynchronously using Celery to avoid timeout issues
- Batch processing (1000 records per batch) for efficient database operations
- Case-insensitive SKU matching using database functions
- Pagination for large product lists
- Indexed database columns for fast queries

## Notes

- The database connection will be configured later. The models are ready and will work once `DATABASE_URL` is set.
- For production, ensure proper error handling, logging, and monitoring.
- Consider adding authentication/authorization for production use.
- Webhook secrets can be used for signing payloads (implementation left for future enhancement).

## License

This project is created for Acme Inc. assignment.

