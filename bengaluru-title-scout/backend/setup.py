#!/usr/bin/env python3
"""
Setup script: installs Python deps, loads .env, and seeds the knowledge base.
Run once before first launch: python backend/setup.py
"""
import os
import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).parent


def run(cmd, **kwargs):
    print(f"  > {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"  [WARN] Command exited with code {result.returncode}")
    return result


def install_deps():
    print("\n[1/3] Installing Python dependencies...")
    run([sys.executable, "-m", "pip", "install", "-r", str(BASE / "requirements.txt"), "--quiet"])


def copy_env():
    env_file    = BASE / ".env"
    env_example = BASE / ".env.example"
    if not env_file.exists() and env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print("[2/3] Created .env from .env.example — fill in your API keys.")
    else:
        print("[2/3] .env already exists.")

    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print("      .env loaded.")
        except ImportError:
            pass


def seed_knowledge_base():
    print("[3/3] Seeding Karnataka law knowledge base into ChromaDB...")
    sys.path.insert(0, str(BASE))
    try:
        from rag.knowledge_base import KnowledgeBase
        kb = KnowledgeBase(persist_dir=str(BASE / "chroma_db"))
        kb.initialize()
        kb.rebuild()
        print(f"      Knowledge base seeded successfully.")
    except Exception as e:
        print(f"      [WARN] KB seed failed: {e}")
        print("      Knowledge base will be built on first API call.")


if __name__ == "__main__":
    print("=" * 55)
    print("  Bengaluru Title Scout — Backend Setup")
    print("=" * 55)
    install_deps()
    copy_env()
    seed_knowledge_base()
    print("\n✓ Setup complete.")
    print("  Start backend : python backend/main.py")
    print("  Start frontend: npm run dev:vite")
    print("  Start all     : npm start")
    print("=" * 55)
