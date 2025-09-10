#!/bin/bash
# Custom shell prompt for the planner project
# Add this to your ~/.bashrc or ~/.zshrc

# Function to check if we're in the planner project
check_planner_project() {
    if [[ "$PWD" == *"/planner"* ]]; then
        if [[ "$VIRTUAL_ENV" != *"/planner/venv"* ]]; then
            echo "⚠️  Remember: Run 'source venv/bin/activate' in this project!"
        else
            echo "✅ Virtual environment active"
        fi
    fi
}

# Custom prompt function
custom_prompt() {
    local status=""
    if [[ "$PWD" == *"/planner"* ]]; then
        if [[ "$VIRTUAL_ENV" == *"/planner/venv"* ]]; then
            status="🐍 "
        else
            status="⚠️  "
        fi
    fi
    
    PS1="${status}\u@\h:\w\$ "
}

# Set the prompt
PROMPT_COMMAND="custom_prompt"

