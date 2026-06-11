"""
Lightweight protobuf reader for douyin live danmaku protobuf messages.

Implements the pure protobuf wire-format primitives needed to decode
PushFrame, Response, Message, ChatMessage, and User types.
"""

import struct
from typing import Optional


class ProtoReader:
    def __init__(self, data: bytes):
        self._buf = data
        self._pos = 0
        self._limit = len(data)

    def _advance(self, count: int) -> int:
        offset = self._pos
        if offset + count > self._limit:
            raise ValueError("Read past limit")
        self._pos += count
        return offset

    def is_at_end(self) -> bool:
        return self._pos >= self._limit

    def push_limit(self) -> int:
        length = self.read_varint32()
        old_limit = self._limit
        self._limit = self._pos + length
        return old_limit

    def pop_limit(self, old_limit: int):
        self._limit = old_limit

    def read_byte(self) -> int:
        return self._buf[self._advance(1)]

    def read_bytes(self, count: int) -> bytes:
        offset = self._advance(count)
        return self._buf[offset:offset + count]

    def read_varint32(self) -> int:
        value = 0
        shift = 0
        while True:
            b = self.read_byte()
            value |= (b & 0x7f) << shift
            shift += 7
            if not (b & 0x80):
                break
        return value

    def read_varint64(self) -> int:
        value = 0
        shift = 0
        while True:
            b = self.read_byte()
            value |= (b & 0x7f) << shift
            shift += 7
            if not (b & 0x80) or shift >= 70:
                break
        return value

    def read_string(self, length: int) -> str:
        raw = self.read_bytes(length)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")

    def skip_field(self, wire_type: int):
        if wire_type == 0:  # varint
            while self.read_byte() & 0x80:
                pass
        elif wire_type == 2:  # length-delimited
            skip_len = self.read_varint32()
            self._advance(skip_len)
        elif wire_type == 5:  # 32-bit
            self._advance(4)
        elif wire_type == 1:  # 64-bit
            self._advance(8)
        else:
            raise ValueError(f"Unknown wire type: {wire_type}")


def decode_pushframe(data: bytes) -> dict:
    r = ProtoReader(data)
    msg: dict = {}
    while not r.is_at_end():
        tag = r.read_varint32()
        field = tag >> 3
        wire = tag & 7
        if field == 0:
            break
        if field == 1:
            msg["seqId"] = r.read_varint64()
        elif field == 2:
            msg["logId"] = r.read_varint64()
        elif field == 3:
            msg["service"] = r.read_varint64()
        elif field == 4:
            msg["method"] = r.read_varint64()
        elif field == 5:
            old = r.push_limit()
            key: Optional[str] = None
            val: Optional[str] = None
            while not r.is_at_end():
                t2 = r.read_varint32()
                f2 = t2 >> 3
                if f2 == 0:
                    break
                if f2 == 1:
                    key = r.read_string(r.read_varint32())
                elif f2 == 2:
                    val = r.read_string(r.read_varint32())
                else:
                    r.skip_field(t2 & 7)
            if key is not None and val is not None:
                headers = msg.setdefault("headersList", {})
                headers[key] = val
            r.pop_limit(old)
        elif field == 6:
            msg["payloadEncoding"] = r.read_string(r.read_varint32())
        elif field == 7:
            msg["payloadType"] = r.read_string(r.read_varint32())
        elif field == 8:
            payload_len = r.read_varint32()
            msg["payload"] = r.read_bytes(payload_len)
        elif field == 9:
            msg["lodIdNew"] = r.read_string(r.read_varint32())
        else:
            r.skip_field(wire)
    return msg


def decode_response(data: bytes) -> dict:
    r = ProtoReader(data)
    msg: dict = {}
    while not r.is_at_end():
        tag = r.read_varint32()
        field = tag >> 3
        wire = tag & 7
        if field == 0:
            break
        if field == 1:
            old = r.push_limit()
            if "messages" not in msg:
                msg["messages"] = []
            msg["messages"].append(decode_message(r))
            r.pop_limit(old)
        elif field == 2:
            msg["cursor"] = r.read_string(r.read_varint32())
        elif field == 3:
            msg["fetchInterval"] = r.read_varint64()
        elif field == 4:
            msg["now"] = r.read_varint64()
        elif field == 5:
            msg["internalExt"] = r.read_string(r.read_varint32())
        elif field == 6:
            msg["fetchType"] = r.read_varint32()
        elif field == 7:
            old = r.push_limit()
            params = msg.setdefault("routeParams", {})
            key: Optional[str] = None
            val: Optional[str] = None
            while not r.is_at_end():
                t2 = r.read_varint32()
                f2 = t2 >> 3
                if f2 == 0:
                    break
                if f2 == 1:
                    key = r.read_string(r.read_varint32())
                elif f2 == 2:
                    val = r.read_string(r.read_varint32())
                else:
                    r.skip_field(t2 & 7)
            if key is not None and val is not None:
                params[key] = val
            r.pop_limit(old)
        elif field == 8:
            msg["heartbeatDuration"] = r.read_varint64()
        elif field == 9:
            msg["needAck"] = r.read_byte() != 0
        elif field == 10:
            msg["pushServer"] = r.read_string(r.read_varint32())
        elif field == 11:
            msg["liveCursor"] = r.read_string(r.read_varint32())
        elif field == 12:
            msg["historyNoMore"] = r.read_byte() != 0
        elif field == 13:
            msg["proxyServer"] = r.read_string(r.read_varint32())
        else:
            r.skip_field(wire)
    return msg


def decode_message(reader) -> dict:
    r = reader if isinstance(reader, ProtoReader) else ProtoReader(reader)
    msg: dict = {}
    while not r.is_at_end():
        tag = r.read_varint32()
        field = tag >> 3
        wire = tag & 7
        if field == 0:
            break
        if field == 1:
            msg["method"] = r.read_string(r.read_varint32())
        elif field == 2:
            payload_len = r.read_varint32()
            msg["payload"] = r.read_bytes(payload_len)
        elif field == 3:
            msg["msgId"] = r.read_varint64()
        elif field == 4:
            msg["msgType"] = r.read_varint32()
        elif field == 5:
            msg["offset"] = r.read_varint64()
        elif field == 6:
            msg["needWrdsStore"] = r.read_byte() != 0
        elif field == 7:
            msg["wrdsVersion"] = r.read_varint64()
        elif field == 8:
            msg["wrdsSubKey"] = r.read_string(r.read_varint32())
        else:
            r.skip_field(wire)
    return msg


def _decode_user_in_place(r: ProtoReader) -> dict:
    """Decode User message from current position in ProtoReader."""
    msg: dict = {}
    while not r.is_at_end():
        tag = r.read_varint32()
        field = tag >> 3
        wire = tag & 7
        if field == 0:
            break
        if field == 1:
            r.skip_field(wire)  # id (int64)
        elif field == 2:
            r.skip_field(wire)  # shortId
        elif field == 3:
            msg["nickname"] = r.read_string(r.read_varint32())
        elif field == 4:
            msg["gender"] = r.read_varint32()
        elif field == 5:
            msg["signature"] = r.read_string(r.read_varint32())
        elif field == 6:
            msg["level"] = r.read_varint32()
        elif field == 7:
            r.skip_field(wire)  # birthday
        elif field == 8:
            msg["telephone"] = r.read_string(r.read_varint32())
        elif field == 14:
            msg["city"] = r.read_string(r.read_varint32())
        elif field == 15:
            msg["status"] = r.read_varint32()
        elif field == 16:
            msg["displayId"] = r.read_string(r.read_varint32())
        elif field == 17:
            msg["secUid"] = r.read_string(r.read_varint32())
        elif field == 18:
            msg["userRole"] = r.read_varint32()
        else:
            r.skip_field(wire)
    return msg


def decode_user(data: bytes) -> dict:
    r = ProtoReader(data)
    return _decode_user_in_place(r)


def decode_chat_message(data: bytes) -> dict:
    r = ProtoReader(data)
    msg: dict = {}
    while not r.is_at_end():
        tag = r.read_varint32()
        field = tag >> 3
        wire = tag & 7
        if field == 0:
            break
        if field == 1:
            r.skip_field(wire)  # Common
        elif field == 2:
            old = r.push_limit()
            msg["user"] = _decode_user_in_place(r)
            r.pop_limit(old)
        elif field == 3:
            msg["content"] = r.read_string(r.read_varint32())
        elif field == 4:
            msg["visibleToSender"] = r.read_byte() != 0
        else:
            r.skip_field(wire)
    return msg


def encode_pushframe(msg: dict) -> bytes:
    result = bytearray()

    def write_varint(value: int):
        while value >= 0x80:
            result.append((value & 0x7f) | 0x80)
            value >>= 7
        result.append(value & 0x7f)

    def write_field(field_num: int, wire_type: int):
        write_varint((field_num << 3) | wire_type)

    def write_string(field_num: int, value: str):
        data = value.encode("utf-8")
        write_field(field_num, 2)
        write_varint(len(data))
        result.extend(data)

    def write_bytes(field_num: int, data: bytes):
        write_field(field_num, 2)
        write_varint(len(data))
        result.extend(data)

    payload_type = msg.get("payloadType", "")
    payload = msg.get("payload", b"")
    log_id = msg.get("logId", "")

    if payload_type:
        write_string(7, payload_type)
    if payload:
        write_bytes(8, payload)
    if log_id:
        write_string(2, log_id)

    return bytes(result)
