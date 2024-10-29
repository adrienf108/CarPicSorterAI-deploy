-- Set working directory to the app's location
set appPath to path to me
set appFolder to POSIX path of (container of appPath as text)

-- Create and activate Python virtual environment
do shell script "cd " & quoted form of appFolder & " && python3.11 -m venv venv"
do shell script "cd " & quoted form of appFolder & " && source venv/bin/activate && pip install -r Requirements.txt"

-- Launch the Streamlit app
do shell script "cd " & quoted form of appFolder & " && source venv/bin/activate && streamlit run main.py"

-- Open the browser
delay 3
do shell script "open http://localhost:8080"