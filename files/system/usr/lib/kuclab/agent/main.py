#!/usr/bin/env python3
"""KucLab Agent: --daemon (sluzba), --chat (popup okno), --ask TEXT (jednorazove)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/usr/lib/kuclab")


def main(argv):
    if "--daemon" in argv:
        import daemon

        daemon.run_server()
        return 0
    if "--ask" in argv:
        i = argv.index("--ask")
        text = argv[i + 1] if i + 1 < len(argv) else ""
        import agent
        import config

        result = agent.Agent(config.load()).ask([{"role": "user", "content": text}])
        print(result["text"])
        return 0
    import chat

    return chat.main()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
