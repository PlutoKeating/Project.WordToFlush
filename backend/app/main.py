import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from app.core.session_manager import SessionManager
from app.core.game_master import GameMaster
from app.core.vector_calculator import VectorCalculator
from app.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

app = FastAPI(
    title="WordToFlush",
    description="AI 驱动的多端弹幕猜词互动游戏系统 API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_calculator = VectorCalculator()
game_master = GameMaster(vector_calculator)
session_manager = SessionManager(game_master)
connection_manager = ConnectionManager()


async def _auto_next_puzzle(room_id: str, delay: float):
    await asyncio.sleep(delay)
    room_state = await session_manager.next_puzzle(room_id)
    if room_state and room_state.current_puzzle:
        await connection_manager.broadcast(
            room_id,
            "game:newPuzzle",
            room_state.current_puzzle.model_dump(by_alias=True),
        )
        await connection_manager.broadcast(
            room_id,
            "game:state",
            room_state.model_dump(by_alias=True),
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/rooms")
async def list_rooms():
    return {"rooms": session_manager.get_active_rooms()}


@app.post("/api/rooms/{room_id}/next-puzzle")
async def next_puzzle(
    room_id: str,
    platform: str = Query("bilibili"),
):
    room = session_manager.get_room(room_id)
    if not room:
        room = await session_manager.create_room(room_id, platform)

    room = await session_manager.next_puzzle(room_id)
    if room and room.current_puzzle:
        puzzle_data = room.current_puzzle.model_dump(by_alias=True)
        state_data = room.model_dump(by_alias=True)
        await connection_manager.broadcast(room_id, "game:newPuzzle", puzzle_data)
        await connection_manager.broadcast(room_id, "game:state", state_data)

    return {
        "status": "ok",
        "puzzle": room.current_puzzle.model_dump(by_alias=True) if room and room.current_puzzle else None,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    current_room_id: str | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            event = message.get("event", "")
            data = message.get("data", {})

            if event == "room:join":
                room_id = data.get("roomId", "default")
                platform = data.get("platform", "bilibili")
                client_id = data.get("clientId", "")

                def _build_composite_key(r: str, c: str) -> str:
                    return f"{r}:{c}" if c else r

                current_room_id = _build_composite_key(room_id, client_id)

                await session_manager.create_room(current_room_id, platform)
                await connection_manager.connect(websocket, current_room_id)

                room_state = session_manager.get_room(current_room_id)
                if room_state:
                    await websocket.send_json({
                        "event": "game:state",
                        "data": room_state.model_dump(by_alias=True),
                    })

            elif event == "room:leave":
                if current_room_id:
                    connection_manager.disconnect(websocket, current_room_id)

            elif event == "game:guess":
                room_id = data.get("roomId", "default")
                client_id = data.get("clientId", "")
                effective_room_id = f"{room_id}:{client_id}" if client_id else (current_room_id or room_id)
                user_id = data.get("userId", "unknown")
                user_name = data.get("userName", "匿名")
                guess = data.get("guess", "")
                if effective_room_id and guess:
                    room_state = session_manager.get_room(effective_room_id)
                    if room_state:
                        try:
                            result = await game_master.process_guess(
                                room_state, user_id, user_name, guess
                            )
                        except Exception:
                            logger.exception("process_guess failed for room=%s", effective_room_id)
                            await websocket.send_json({
                                "event": "error",
                                "data": {"message": "处理猜测时出错，请重试"},
                            })
                            continue
                        if result:
                            record = result["record"]
                            await connection_manager.broadcast(
                                effective_room_id,
                                "game:guessResult",
                                record.model_dump(by_alias=True),
                            )
                            await connection_manager.broadcast(
                                effective_room_id,
                                "game:state",
                                room_state.model_dump(by_alias=True),
                            )
                            if result["solved"]:
                                await connection_manager.broadcast(
                                    effective_room_id,
                                    "game:puzzleSolved",
                                    {
                                        "word": room_state.current_puzzle.word if room_state.current_puzzle else "",
                                        "solvedBy": room_state.solved_by,
                                    },
                                )
                                asyncio.create_task(
                                    _auto_next_puzzle(effective_room_id, 3.0)
                                )

            elif event == "game:nextPuzzle":
                room_id = data.get("roomId", "default")
                client_id = data.get("clientId", "")
                effective_room_id = f"{room_id}:{client_id}" if client_id else (current_room_id or room_id)
                if effective_room_id:
                    room_state = await session_manager.next_puzzle(effective_room_id)
                    if room_state and room_state.current_puzzle:
                        await connection_manager.broadcast(
                            effective_room_id,
                            "game:newPuzzle",
                            room_state.current_puzzle.model_dump(by_alias=True),
                        )
                        await connection_manager.broadcast(
                            effective_room_id,
                            "game:state",
                            room_state.model_dump(by_alias=True),
                        )

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error in room=%s", current_room_id)
    finally:
        if current_room_id:
            connection_manager.disconnect(websocket, current_room_id)
