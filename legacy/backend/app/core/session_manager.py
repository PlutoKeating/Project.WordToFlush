from app.models.game import Platform, RoomState
from app.core.game_master import GameMaster


class SessionManager:
    def __init__(self, game_master: GameMaster):
        self._rooms: dict[str, RoomState] = {}
        self.game_master = game_master

    async def create_room(self, room_id: str, platform: Platform) -> RoomState:
        if room_id in self._rooms:
            return self._rooms[room_id]

        room_state = await self.game_master.create_room(room_id, platform)
        self._rooms[room_id] = room_state
        return room_state

    def get_room(self, room_id: str) -> RoomState | None:
        return self._rooms.get(room_id)

    async def next_puzzle(self, room_id: str) -> RoomState | None:
        room = self._rooms.get(room_id)
        if not room:
            return None

        await self.game_master.next_puzzle(room)
        return room

    def remove_room(self, room_id: str) -> None:
        self._rooms.pop(room_id, None)

    def get_active_rooms(self) -> list[str]:
        return list(self._rooms.keys())
