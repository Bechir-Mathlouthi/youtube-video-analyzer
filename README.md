# YouTube Video Analyzer

A Python tool that combines AgentQL and Grok-2 to analyze YouTube videos and generate comprehensive markdown reports.

## Features

- Scrapes YouTube video data using AgentQL
- Analyzes video content and metadata
- Formats results using Grok-2 AI
- Generates detailed markdown reports

## Installation

1. Clone the repository:


git clone https://github.com/Bechir-Mathlouthi/youtube-video-analyzer.git

2. Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
agentql init
```

4. Create a `.env` file in the project root and add your API keys:

```bash
XAI_API_KEY=your-grok-api-key
AGENTQL_API_KEY=your-agentql-api-key
```

## Usage

Run the analyzer:

```bash
python main_agent.py
```

The script will generate a markdown file with the analysis results in your current directory.

## Requirements

- Python 3.7+
- AgentQL API key
- Grok-2 API key

## Author

[Bechir Mathlouthi](https://github.com/Bechir-Mathlouthi)

## License

MIT License