import os
import shutil
import argparse
from pathlib import Path

AGENTS = {
    "claude-code": {
        "check_dir": "~/.claude",
        "install_dir": "~/.claude/skills/linkedin-analyzer",
        "files": ["claude-code/SKILL.md"],
    },
    "claude-code-talent-scout": {
        "check_dir": "~/.claude",
        "install_dir": "~/.claude/skills/talent-scout",
        "files": ["claude-code/talent-scout/SKILL.md"],
    },
    "codex": {
        "check_dir": "~/.codex",
        "install_dir": "~/.codex/skills/linkedin-analyzer",
        "files": ["codex/SKILL.md", "codex/agents/openai.yaml"],
    },
    "cursor": {
        "check_dir": "~/.cursor",  # Global cursor rules
        "install_dir": "~/.cursor/rules",
        "files": ["cursor/linkedin-analyzer.mdc"],
    },
    "antigravity": {
        "check_dir": "~/.gemini/antigravity",
        "install_dir": "~/.gemini/antigravity/skills/linkedin-analyzer",
        "files": ["antigravity/SKILL.md"],
    },
    "openclaw": {
        "check_dir": "~/.openclaw",
        "install_dir": "~/.openclaw/skills/linkedin-analyzer",
        "files": ["openclaw/SKILL.md"],
    },
    "zeroclaw": {
        "check_dir": "~/.zeroclaw",
        "install_dir": "~/.zeroclaw/workspace/skills/linkedin-analyzer",
        "files": ["zeroclaw/SKILL.md", "zeroclaw/trait.toml"],
    },
}


def expand(path_str: str) -> Path:
    return Path(os.path.expanduser(path_str))


def detect_agents() -> list[str]:
    detected = []
    for agent, config in AGENTS.items():
        if expand(config["check_dir"]).exists():
            detected.append(agent)
    return detected


def install_for_agent(agent: str, source_base: Path):
    if agent not in AGENTS:
        print(f"Unknown agent: {agent}")
        return False

    config = AGENTS[agent]
    target_dir = expand(config["install_dir"])

    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        for file_path in config["files"]:
            src = source_base / file_path

            # If it's a deep file like codex/agents/openai.yaml, preserve structure inside target
            rel_path = Path(file_path).relative_to(Path(file_path).parts[0])
            dst = target_dir / rel_path

            dst.parent.mkdir(parents=True, exist_ok=True)

            if src.exists():
                shutil.copy2(src, dst)
                print(f"  ✓ Copied {src.name} -> {dst}")
            else:
                print(f"  ! Source file missing: {src}")

        print(f"Successfully installed linkedin-analyzer for {agent}")
        return True
    except Exception as e:
        print(f"Error installing for {agent}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Install ai-native-toolkit skills for AI Agents"
    )
    parser.add_argument("--list", action="store_true", help="List detected agents")
    parser.add_argument(
        "--agent",
        type=str,
        choices=list(AGENTS.keys()) + ["all"],
        default="all",
        help="Specific agent to install for",
    )

    args = parser.parse_args()

    # Needs to be run from the root of the repo, or find integrations/ folder
    current_dir = Path(__file__).parent.absolute()

    if args.list:
        detected = detect_agents()
        print("Detected AI Agents:")
        for agent in AGENTS.keys():
            mark = "✓" if agent in detected else " "
            print(f"[{mark}] {agent}")
        return

    targets = detect_agents() if args.agent == "all" else [args.agent]

    if not targets:
        print("No supported AI agents found on this system.")
        return

    print(f"Installing linkedin-analyzer skill for: {', '.join(targets)}")
    for agent in targets:
        install_for_agent(agent, current_dir)

    print("\nNext steps:")
    print("1. Ensure the toolkit is installed: `pip install -e .`")
    print("2. Set your preferred API keys in your environment:")
    print("   export APIFY_API_KEY='...'")
    print("   export GEMINI_API_KEY='...' (or OPENAI_API_KEY, ANTHROPIC_API_KEY)")
    print("3. Restart your AI agent and ask it to analyze a LinkedIn profile!")


if __name__ == "__main__":
    main()
