# 🎙️ OpenClaw Meeting Assistant

AI-powered meeting assistant specifically built for OpenClaw on VPS.

## 🎯 Features

- **Upload-Based Workflow** (perfect for VPS/headless servers)
- **Multi-Provider Transcription** (OpenAI Whisper API, local whisper.cpp, Deepgram)
- **AI Analysis** (Claude Sonnet 4.5 for action items, decisions, summaries)
- **Human-in-the-Loop Review** (Telegram-based approval flow)
- **QPS-Standard Protocols** (Professional meeting templates)
- **Odoo Integration** (Action items → Tasks after review)
- **M365 Calendar Context** (Auto-fill meeting details)
- **Memory/Knowledge Base** (Cross-meeting search)

## 🏗️ Architecture

```
Meeting Audio → Upload → Transcription → AI Analysis → Review (Telegram) → Export (Odoo/Email/Memory)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API Key (for Whisper & analysis)
- Anthropic API Key (for Claude)
- Odoo credentials (existing config from openclaw workspace)
- M365 credentials (existing from openclaw workspace)

### Installation

```bash
git clone https://github.com/sruppelQPS/openclaw-meeting-assistant.git
cd openclaw-meeting-assistant
pip install -r requirements.txt
```

### Configuration

Create `config.json`:

```json
{
  "transcription": {
    "provider": "openai-whisper",
    "model": "whisper-1",
    "language": "de"
  },
  "analysis": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-5"
  },
  "odoo": {
    "config_path": "~/.openclaw/workspace/skills/odoo-connector/config.json",
    "contacts_path": "~/.openclaw/workspace/odoo-contacts.json"
  },
  "m365": {
    "calendar_path": "~/.openclaw/secrets/m365-calendar/work.json"
  }
}
```

### Usage

```bash
# Process meeting audio
python scripts/process_meeting.py meeting.mp3 \
  --type team \
  --attendees "Serg, Babak, Julia"

# Review via Telegram (interactive)
# Export after approval
```

## 📁 Project Structure

```
openclaw-meeting-assistant/
├── src/
│   ├── transcription/      # Whisper API, whisper.cpp, Deepgram
│   ├── analysis/           # Claude-based analysis (action items, decisions)
│   ├── protocol/           # Protocol generation (Markdown, PDF, DOCX)
│   ├── integrations/       # Odoo, M365, Telegram, Memory
│   └── utils/              # Helpers, fuzzy matching, etc.
├── templates/
│   ├── protocol-qps.md     # QPS standard template
│   ├── protocol-quick.md   # Quick meeting notes
│   └── protocol-full.md    # Full transcript version
├── scripts/
│   ├── process_meeting.py  # Main entry point
│   ├── upload_handler.sh   # Telegram upload receiver
│   └── install_whisper.sh  # Install whisper.cpp locally
├── tests/
├── requirements.txt
├── config.json.example
└── README.md
```

## 🔄 Development Status

### ✅ Phase 1: Core (Sonnet 4.5)
- [x] Project structure
- [ ] Transcription module (OpenAI Whisper)
- [ ] Basic AI analysis (Claude)
- [ ] Protocol generation (Markdown)
- [ ] Odoo contact matching
- [ ] M365 calendar context

### 🔄 Phase 2: Integration (Opus 4.6 - later)
- [ ] Telegram review flow
- [ ] State management
- [ ] Error handling
- [ ] Odoo task creation
- [ ] Memory integration
- [ ] Complete end-to-end testing

## 💰 Cost Optimization

- **Whisper API:** ~$0.006/min ($0.36 for 1h meeting)
- **Claude Analysis:** ~$0.10-0.30 per meeting
- **Total:** ~$0.50-0.70 per meeting
- **Local Whisper:** $0 (only Claude costs)

Compare: Otter.ai Pro = $16.99/month, Fireflies = $18.99/month

## 📝 License

MIT

## 👨‍💻 Author

Built for QPS Engineering AG with OpenClaw
