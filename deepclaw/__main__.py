"""Run deepclaw voice agent server."""

import sys

from .voice_agent_server import main, run_doctor

if __name__ == "__main__":
    if "doctor" in sys.argv[1:]:
        sys.exit(run_doctor())
    main()
