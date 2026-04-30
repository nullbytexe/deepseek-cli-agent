
# DeepSeek Auto Builder CLI 🤖

A locally running, interactive CLI agent that automates the [DeepSeek Chat](https://chat.deepseek.com) web interface to automatically scaffold projects, write code files, and execute terminal commands on your Windows machine.

## 🎯 Purpose
The main goal of this project is to automatically create a **baseline for building**. Think of it as a way to quickly scaffold a first "draft" of your project. Because DeepSeek is extremely generous with its token generation, this tool is perfect for laying down foundational code, creating boilerplate, and generating multiple files in a single run before you step in to refine it. 

It does this without requiring an official API key—it simply uses your browser!

## ⚙️ How It Works
Instead of using paid APIs, this script uses **Playwright** to connect to an active Chrome browser session. It acts as an automated user that types prompts, waits for DeepSeek to finish thinking, and clicks the "Copy" button to extract the code.

The workflow is highly interactive and safe (Human-in-the-Loop):
1. **Planning Phase:** The agent asks DeepSeek to create a step-by-step plan based on your prompt. 
2. **Review:** You review the plan in the terminal. You can approve it, or type feedback to force DeepSeek to rewrite the plan.
3. **Execution Loop:** DeepSeek outputs PowerShell commands (using `Heredoc` syntax to create files). 
4. **Safety Check:** *Before any command runs*, the script pauses and asks for your permission (`y`/`n` or type your own command).
5. **Feedback Loop:** Once a command runs, the script captures the system output (STDOUT/STDERR) and feeds it back to DeepSeek. If there is an error, DeepSeek automatically tries to fix it!

## ✨ Key Features
- **Free to Use:** Operates via web UI automation, no API credits required.
- **Self-Correcting:** Feeds terminal errors back to the AI for automatic debugging.
- **Human-in-the-Loop (HITL):** Never runs dangerous system commands without your explicit `y/n` approval.
- **Native Windows Support:** Optimized for PowerShell file creation and folder management.

---

## 🛠️ Prerequisites
1. **Python 3.8+**
2. **Google Chrome** installed on your machine.
3. An active account logged into [DeepSeek Chat](https://chat.deepseek.com).

## 📦 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/deepseek-cli-agent.git
   cd deepseek-cli-agent
   ```
2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install the Playwright browser binaries:
   ```bash
   playwright install chromium
   ```

## 🚀 Usage

**IMPORTANT:** Because this agent interacts with your active browser, you must start Google Chrome in **remote debugging mode** before running the script.

1. **Fully close all running instances of Google Chrome.**
2. Open your Command Prompt (CMD) or PowerShell and run this command to open a debuggable Chrome window:
   ```cmd
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
   ```
   *(Note: Adjust the path if Chrome is installed somewhere else on your PC).*
3. In this new Chrome window, go to `https://chat.deepseek.com` and make sure you are logged in.
4. Keep the DeepSeek tab open, go back to your terminal, and run the agent with your project prompt:
   ```bash
   python main.py "Create a Flask web server with 2 APIs that returns JSON data"
   ```

## ⚠️ Disclaimer
This tool executes system commands locally on your machine. Always review the PowerShell commands suggested by the AI before typing `y` to approve them.
