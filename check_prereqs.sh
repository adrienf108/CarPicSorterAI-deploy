#!/bin/bash

# Check for Python 3.11
if ! command -v python3.11 &> /dev/null; then
    osascript -e 'display dialog "Python 3.11 is required. Install now?" buttons {"Yes", "No"} default button "Yes"'
    if [ $? -eq 0 ]; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        brew install python@3.11
    else
        exit 1
    fi
fi

# Check for PostgreSQL
if ! command -v postgres &> /dev/null; then
    osascript -e 'display dialog "PostgreSQL is required. Install now?" buttons {"Yes", "No"} default button "Yes"'
    if [ $? -eq 0 ]; then
        brew install postgresql@15
        brew services start postgresql@15
    else
        exit 1
    fi
fi 