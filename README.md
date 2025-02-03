# Slack-Ollama Bot

A Slack bot that uses Ollama's local LLM capabilities to provide AI-powered responses and thread summarization. Name suggestions are welcome :) 

## Features

### 1. Thread Summarization
- **Public Summary**: Get a summary of any Slack thread that's visible to all users
  ```
  @BotName summarize thread
  ```
  or
  ```
  @BotName thread summary
  ```

- **Private Summary**: Get a thread summary that's only visible to you
  ```
  @BotName summarize thread private
  ```
  or
  ```
  @BotName thread summary me only
  ```

### 2. General Chat
- The bot can respond to general questions and engage in conversations
- Uses local LLM through Ollama for responses
- All responses are context-aware and thread-based

## Prerequisites

1. [Ollama](https://ollama.ai/) installed on your machine
2. Python 3.8 or higher
3. A Slack workspace where you can install apps

## Setup Instructions

### 1. Slack App Configuration

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App"
   - Choose "From scratch"
   - Name your app
   - Select your workspace

3. Under "Basic Information":
   - Note down the "Signing Secret"
   - Scroll down to "App-Level Tokens"
   - Click "Generate Token and Scopes"
   - Add the `connections:write` scope
   - Name the token and create it
   - Save the generated app token (starts with `xapp-`)

4. Under "OAuth & Permissions":
   - Add the following Bot Token Scopes:
     - `app_mentions:read`
     - `channels:history`
     - `chat:write`
     - `groups:history`
     - `im:history`
     - `mpim:history`
     - `users:read`
   - Install the app to your workspace
   - Save the Bot User OAuth Token (starts with `xoxb-`)

5. Under "Socket Mode":
   - Enable Socket Mode

6. Under "Event Subscriptions":
   - Enable Events
   - Subscribe to bot events:
     - Add `app_mentions`

### 2. Local Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/slack-ollama.git
cd slack-ollama
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token
OLLAMA_MODEL=llama3.2:latest
OLLAMA_HOST=http://localhost:11434
```

5. Start Ollama and pull the required model:
```bash
ollama run llama3.2:latest
```

6. Run the bot:
```bash
python agent.py
```

## Usage

1. Invite the bot to a channel:
```
/invite @YourBotName
```

2. Mention the bot with your request:
   - For general questions:
     ```
     @BotName How does photosynthesis work?
     ```
   - For thread summaries:
     ```
     @BotName summarize thread
     ```
   - For private thread summaries:
     ```
     @BotName summarize thread private
     ```

## Error Handling

The bot provides clear error messages for common issues:
- Missing permissions
- Unable to access thread history
- Connection issues with Ollama
- Invalid commands

## Development

The bot is built using:
- [Slack Bolt for Python](https://slack.dev/bolt-python/concepts)
- [LangChain](https://python.langchain.com/docs/get_started/introduction)
- [Ollama](https://ollama.ai/docs)

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[MIT License](LICENSE)
