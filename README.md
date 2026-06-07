# Echo - The Game That Learns With You

NeuroFlux v1: A self-adapting cognitive game using heuristic struggle detection and
procedural puzzle generation. Built with FastAPI + React + Ollama on ARM64.

## Architecture

- Contabo VPS (173.249.11.188): Frontend + FastAPI backend + SQLite + Nginx
- Netcup VPS (89.58.33.163): Ollama models (Qwen2.5-Coder-7B + Qwen2.5-3B) + training
- Domain: game.benjaminsquare.com

## Structure

```
/root/Echo/
├── backend/          # FastAPI application
│   ├── main.py       # API entrypoint
│   ├── engine.py     # Adaptive game engine (heuristic)
│   ├── models.py     # SQLite schemas
│   ├── auth.py       # JWT auth
│   ├── llm_client.py # Ollama hint client
│   └── config.py     # Settings
├── frontend/         # React + Vite game client
│   ├── src/
│   │   ├── App.tsx
│   │   ├── game/     # Puzzle engine + Canvas
│   │   ├── auth/     # Login/register
│   │   └── dashboard/ # Player metrics
│   └── package.json
├── infra/            # Nginx, systemd, deployment
└── README.md
```