# 🚀 Quick Start Guide - Minecraft Omni-Builder v3.1

Get your AI Minecraft builder running in 5 minutes!

## Step 1: Install Python Dependencies

```bash
cd minecraft_omni
pip install -r requirements.txt
```

## Step 2: Configure Your Setup

Edit the `config.yaml` file with your settings:

```bash
nano config.yaml
# or use any text editor
```

### Required Settings:

#### 1. MemPalace (Memory Backend)
```yaml
mempalace:
  url: "https://api.mempalace.io"  # Or your self-hosted URL
  api_key: "YOUR_API_KEY_HERE"     # Get from https://mempalace.io/dashboard
  project_id: "my_minecraft_bot"
```

#### 2. Local LLM (The Brain)
```yaml
llm:
  provider: "ollama"      # Options: ollama, lm_studio, openai
  model: "llama3"         # Make sure this model is installed
  base_url: "http://localhost:11434/v1"
```

**For Ollama users:**
```bash
# Install Ollama first: https://ollama.ai
ollama pull llama3
ollama serve
```

#### 3. Minecraft Server (The Hands)
```yaml
minecraft:
  method: "rcon"
  host: "localhost"
  port: 25575
  password: "your_rcon_password"  # Set in server.properties
```

**Enable RCON in your Minecraft server:**
Edit `server.properties`:
```
enable-rcon=true
rcon.password=your_rcon_password
rcon.port=25575
```

## Step 3: Run the Bot

```bash
python run.py
```

The launcher will automatically:
- ✅ Check and install missing packages
- ✅ Test MemPalace connection
- ✅ Verify LLM is running
- ✅ Check Minecraft server access
- ✅ Start the interactive bot

## Step 4: Start Building!

Once running, type commands like:

```
!bot build a wooden house at 100,64,200
!bot create a castle with towers
!bot undo last action
!bot preview a bridge over the river
!bot help
```

## Troubleshooting

### ❌ "Cannot connect to Ollama"
```bash
# Start Ollama service
ollama serve

# Pull the model if not exists
ollama pull llama3
```

### ❌ "MemPalace connection failed"
- Check your API key in config.yaml
- Ensure you have internet connection
- Visit https://mempalace.io/dashboard to get a key

### ❌ "RCON connection refused"
- Make sure RCON is enabled in server.properties
- Check firewall settings for port 25575
- Verify password matches exactly

### ❌ Missing packages
```bash
pip install --upgrade -r requirements.txt
```

## Next Steps

- 📖 Read full documentation: `README.md`
- 🎮 Install Fabric mod for holographic preview
- 🌐 Set up PostgreSQL for multi-server sync
- 🤖 Customize LLM prompts in `llm/` directory

---

**Need Help?** 
- GitHub Issues: https://github.com/Darkstorm-bot/minecraft_omni/issues
- Discord: [Join our server]
