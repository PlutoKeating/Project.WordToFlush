import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.session_manager import SessionManager
from app.core.game_master import GameMaster
from app.core.vector_calculator import VectorCalculator
from app.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

GLOBAL_ROOM = "global"

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


async def _auto_next_puzzle(delay: float):
    await asyncio.sleep(delay)
    room_state = await session_manager.next_puzzle(GLOBAL_ROOM)
    if room_state and room_state.current_puzzle:
        await connection_manager.broadcast(
            GLOBAL_ROOM,
            "game:newPuzzle",
            room_state.current_puzzle.model_dump(by_alias=True),
        )
        await connection_manager.broadcast(
            GLOBAL_ROOM,
            "game:state",
            room_state.model_dump(by_alias=True),
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/rooms")
async def list_rooms():
    return {"rooms": [GLOBAL_ROOM]}


@app.post("/api/next-puzzle")
async def next_puzzle():
    room = session_manager.get_room(GLOBAL_ROOM)
    if not room:
        room = await session_manager.create_room(GLOBAL_ROOM, "bilibili")

    room = await session_manager.next_puzzle(GLOBAL_ROOM)
    if room and room.current_puzzle:
        puzzle_data = room.current_puzzle.model_dump(by_alias=True)
        state_data = room.model_dump(by_alias=True)
        await connection_manager.broadcast(GLOBAL_ROOM, "game:newPuzzle", puzzle_data)
        await connection_manager.broadcast(GLOBAL_ROOM, "game:state", state_data)

    return {
        "status": "ok",
        "puzzle": room.current_puzzle.model_dump(by_alias=True) if room and room.current_puzzle else None,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            event = message.get("event", "")
            data = message.get("data", {})

            if event == "room:join":
                is_first = session_manager.get_room(GLOBAL_ROOM) is None

                if is_first:
                    await session_manager.create_room(GLOBAL_ROOM, "bilibili")

                await connection_manager.connect(websocket, GLOBAL_ROOM)

                if is_first:
                    room_state = await session_manager.next_puzzle(GLOBAL_ROOM)
                    if room_state and room_state.current_puzzle:
                        await connection_manager.broadcast(
                            GLOBAL_ROOM,
                            "game:newPuzzle",
                            room_state.current_puzzle.model_dump(by_alias=True),
                        )
                        await connection_manager.broadcast(
                            GLOBAL_ROOM,
                            "game:state",
                            room_state.model_dump(by_alias=True),
                        )
                else:
                    room_state = session_manager.get_room(GLOBAL_ROOM)
                    if room_state:
                        await websocket.send_json({
                            "event": "game:state",
                            "data": room_state.model_dump(by_alias=True),
                        })
                        if room_state.current_puzzle:
                            await websocket.send_json({
                                "event": "game:newPuzzle",
                                "data": room_state.current_puzzle.model_dump(by_alias=True),
                            })

            elif event == "room:leave":
                connection_manager.disconnect(websocket, GLOBAL_ROOM)

            elif event == "game:guess":
                user_id = data.get("userId", "unknown")
                user_name = data.get("userName", "")
                guess = data.get("guess", "")

                if guess:
                    room_state = session_manager.get_room(GLOBAL_ROOM)
                    if room_state:
                        try:
                            result = await game_master.process_guess(
                                room_state, user_id, user_name, guess
                            )
                        except Exception:
                            logger.exception("process_guess failed")
                            await websocket.send_json({
                                "event": "error",
                                "data": {"message": "处理猜测时出错，请重试"},
                            })
                            continue
                        if result:
                            record = result["record"]
                            await connection_manager.broadcast(
                                GLOBAL_ROOM,
                                "game:guessResult",
                                record.model_dump(by_alias=True),
                            )
                            await connection_manager.broadcast(
                                GLOBAL_ROOM,
                                "game:state",
                                room_state.model_dump(by_alias=True),
                            )
                            if result["solved"]:
                                await connection_manager.broadcast(
                                    GLOBAL_ROOM,
                                    "game:puzzleSolved",
                                    {
                                        "word": room_state.current_puzzle.word if room_state.current_puzzle else "",
                                        "solvedBy": room_state.solved_by,
                                    },
                                )
                                asyncio.create_task(_auto_next_puzzle(3.0))

            elif event == "game:nextPuzzle":
                room_state = await session_manager.next_puzzle(GLOBAL_ROOM)
                if room_state and room_state.current_puzzle:
                    await connection_manager.broadcast(
                        GLOBAL_ROOM,
                        "game:newPuzzle",
                        room_state.current_puzzle.model_dump(by_alias=True),
                    )
                    await connection_manager.broadcast(
                        GLOBAL_ROOM,
                        "game:state",
                        room_state.model_dump(by_alias=True),
                    )

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        connection_manager.disconnect(websocket, GLOBAL_ROOM)
