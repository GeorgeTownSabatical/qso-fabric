from __future__ import annotations

import argparse
import json
import sys

from mcp_qso_edu.protocol_server import QSOEduMCPProtocolServer


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="qso-chat")
    parser.add_argument("session_token", help="Stable token used to derive sandbox_id")
    parser.add_argument("--author")
    parser.add_argument("--role")
    parser.add_argument("--content", help="Message content (stdin if omitted)")
    parser.add_argument("--tail", type=int)
    parser.add_argument("--conversation-id", default="main")
    args = parser.parse_args(argv)

    server = QSOEduMCPProtocolServer()
    # Derive/ensure sandbox context from a stable session token.
    sandbox_info = server.call_tool("qso.create_sandbox", {"session_token": args.session_token})
    sandbox_id = sandbox_info["sandbox_id"]
    server.call_tool(
        "qso.chat.init",
        {"sandbox_id": sandbox_id, "conversation_id": args.conversation_id},
    )

    if args.tail:
        out = server.call_tool(
            "qso.chat.tail",
            {
                "sandbox_id": sandbox_id,
                "conversation_id": args.conversation_id,
                "limit": args.tail,
            },
        )
        print(json.dumps(out, indent=2))
        return

    if not args.author or not args.role:
        raise SystemExit("--author and --role are required when appending")

    content = (args.content or sys.stdin.read()).strip()
    if not content:
        raise SystemExit("content is empty")

    out = server.call_tool(
        "qso.chat.append",
        {
            "sandbox_id": sandbox_id,
            "conversation_id": args.conversation_id,
            "author": args.author,
            "role": args.role,
            "content": content,
        },
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
