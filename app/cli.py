"""Interactive chat with the assistant in the terminal.

    make chat
"""

import asyncio

from app.agent import AgentService, new_session_id
from app.search import load_search_index


async def main() -> None:
    service = AgentService(load_search_index())
    session_id = new_session_id()
    print("NovaMart assistant. Ask about policy or an order (NM-XXXXX). Ctrl-D to exit.")
    while True:
        try:
            question = input("\nyou> ").strip()
        except EOFError:
            print()
            return
        if not question:
            continue
        reply = await service.ask(session_id, question)
        print(f"\nassistant> {reply.answer}")
        details = []
        if reply.tool_calls:
            names = ", ".join(c["name"] for c in reply.tool_calls)
            details.append(f"tools: {names}")
        if reply.citations:
            details.append(f"sources: {', '.join(reply.citations)}")
        if reply.refused:
            details.append("refused: logged to knowledge gaps")
        details.append(f"{reply.latency_ms} ms")
        print(f"           [{' | '.join(details)}]")


if __name__ == "__main__":
    asyncio.run(main())
