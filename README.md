# Car Image Categorization Web App - Local Mac Deployment Guide

## Overview
This application uses AI-powered image recognition to categorize car images into predefined categories and subcategories. It features user authentication, batch upload capabilities, and an advanced analytics dashboard.

## Prerequisites

### Software Requirements
1. Python 3.11 or later:
```bash
brew install python@3.11
```

2. PostgreSQL 15:
```bash
brew install postgresql@15
brew services start postgresql@15
```

### API Requirements
- Anthropic API key (for Claude 3 Opus model)
  - Sign up at https://www.anthropic.com/
  - Generate an API key from your dashboard
  - Keep this key secure and never share it

## Installation Steps

1. Clone the repository:
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

2. Access the application:
```
http://localhost:5000
```

## Features
- AI-powered image categorization using Claude 3 Opus
- User authentication with role-based access
- Batch upload functionality
- Advanced analytics dashboard
- Duplicate image detection
- Manual review and correction capabilities

## Important Notes

### Security
1. Never share your `.env` file or API keys
2. Use strong passwords for database access
3. Keep your Python packages updated for security patches
4. The first registered user becomes an admin automatically

### Performance
1. Maximum upload size is set to 1000MB
2. Batch uploads show progress indicators
3. Duplicate images are automatically detected and skipped

## Troubleshooting

### Database Issues
1. Verify PostgreSQL is running:
```bash
brew services list
```

2. Check database existence:
```bash
psql -l
```

3. Test database connection:
```bash
psql -h localhost -U your_postgres_username your_database_name
```

### Application Issues
1. Import errors:
   - Verify installations: `pip list`
   - Check Python version: `python --version`

2. Server issues:
   - Check port availability: `lsof -i :5000`
   - Verify environment variables: `env | grep PG`

3. API issues:
   - Verify Anthropic API key is correctly set
   - Check API access in environment variables

### Common Solutions
- Clear browser cache if the interface appears broken
- Restart the application after configuration changes
- Ensure sufficient disk space for image storage
- Check database logs for connection issues

## Support
For additional support or to report issues, please use the repository's issue tracker.
