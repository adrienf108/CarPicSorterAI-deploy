# Car Image Categorization Web App - Local Mac Deployment Guide

## Prerequisites

1. Install Python 3.11 or later using Homebrew:
```bash
brew install python@3.11
```

2. Install PostgreSQL using Homebrew:
```bash
brew install postgresql@15
brew services start postgresql@15
```

## Installation Steps

1. Clone the repository to your local machine:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Install the required Python packages:
```bash
pip install -r Requirements.txt
```

3. Set up environment variables by creating a `.env` file:
```bash
ANTHROPIC_API_KEY=your_anthropic_api_key
PGHOST=localhost
PGPORT=5432
PGUSER=your_postgres_username
PGPASSWORD=your_postgres_password
PGDATABASE=your_database_name
DATABASE_URL=postgresql://your_postgres_username:your_postgres_password@localhost:5432/your_database_name
```

4. Create a PostgreSQL database:
```bash
createdb your_database_name
```

## Configuration

1. Create the `.streamlit` directory and configuration file:
```bash
mkdir -p .streamlit
```

2. Create `.streamlit/config.toml` with the following content:
```toml
[server]
headless = true
address = "0.0.0.0"
port = 5000
maxUploadSize = 1000
```

## Running the Application

1. Start the Streamlit application:
```bash
streamlit run main.py
```

2. Access the application in your web browser at:
```
http://localhost:5000
```

## Important Notes

1. Make sure PostgreSQL is running before starting the application.
2. Ensure you have a valid Anthropic API key for image recognition functionality.
3. The first user to register will automatically become an admin.
4. The application requires sufficient disk space for storing uploaded images.

## Troubleshooting

1. If you encounter database connection issues:
   - Verify PostgreSQL is running: `brew services list`
   - Check your database credentials in the `.env` file
   - Ensure the database exists: `psql -l`

2. If you see import errors:
   - Verify all dependencies are installed: `pip list`
   - Check your Python version: `python --version`

3. If the application fails to start:
   - Check if port 5000 is available: `lsof -i :5000`
   - Verify all environment variables are set: `env | grep PG`

## Security Notes

1. Never share your `.env` file or API keys
2. Use strong passwords for database access
3. Keep your Python packages updated for security patches
