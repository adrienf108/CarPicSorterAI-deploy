#!/bin/bash

# Set paths
APP_PATH="/Applications/Car Image Sorter.app"
RESOURCES_DIR="$APP_PATH/Contents/Resources"

# Create Resources directory if it doesn't exist
mkdir -p "$RESOURCES_DIR"

# Copy all your Python files
cp main.py "$RESOURCES_DIR"
cp ai_model.py "$RESOURCES_DIR"
cp custom_model.py "$RESOURCES_DIR"
cp database.py "$RESOURCES_DIR"
cp image_utils.py "$RESOURCES_DIR"
cp setup_config.py "$RESOURCES_DIR"

# Copy shell scripts
cp check_prereqs.sh "$RESOURCES_DIR"
cp run_app.sh "$RESOURCES_DIR"

# Set permissions
chmod +x "$RESOURCES_DIR"/*.sh

# Create Requirements.txt
echo "anthropic>=0.37.1
bcrypt>=4.2.0
flask-login>=0.6.3
numpy>=1.26.4
pandas>=2.2.3
pillow>=10.4.0
plotly>=5.24.1
psycopg2-binary>=2.9.10
python-dotenv
streamlit>=1.39.0
tensorflow>=1.0.1" > "$RESOURCES_DIR/Requirements.txt" 