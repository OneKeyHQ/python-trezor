# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import logging
import struct
from typing import Tuple

from typing_extensions import Protocol as StructuralType

from . import MessagePayload, Transport

REPLEN = 64
BLE_REPLEN = 192
REPLEN_NFC = 1024
V2_FIRST_CHUNK = 0x01
V2_NEXT_CHUNK = 0x02
V2_BEGIN_SESSION = 0x03
V2_END_SESSION = 0x04
PROCESS_REPORTER = None
HTTP = False
OFFSET = 0
TOTAL = 0

LOG = logging.getLogger(__name__)


class Handle(StructuralType):
    """PEP 544 structural type for Handle functionality.
    (called a "Protocol" in the proposed PEP, name which is impractical here)

    Handle is a "physical" layer for a protocol.
    It can open/close a connection and read/write bare data in 64-byte chunks.

    Functionally we gain nothing from making this an (abstract) base class for handle
    implementations, so this definition is for type hinting purposes only. You can,
    but don't have to, inherit from it.
    """

    def open(self) -> None:
        ...

    def close(self) -> None:
        ...

    def read_chunk(self) -> bytes:
        ...

    def write_chunk(self, chunk: bytes) -> None:
        ...

    def write_chunk_nfc(self, chunk: bytearray) -> bytes:
        ...

    def read_ble(self) -> bytes:
        ...


class Protocol:
    """Wire protocol that can communicate with a Trezor device, given a Handle.

    A Protocol implements the part of the Transport API that relates to communicating
    logical messages over a physical layer. It is a thing that can:
    - open and close sessions,
    - send and receive protobuf messages,
    given the ability to:
    - open and close physical connections,
    - and send and receive binary chunks.

    For now, the class also handles session counting and opening the underlying Handle.
    This will probably be removed in the future.

    We will need a new Protocol class if we change the way a Trezor device encapsulates
    its messages.
    """

    def __init__(self, handle: Handle) -> None:
        self.handle = handle
        self.session_counter = 0

    # XXX we might be able to remove this now that TrezorClient does session handling
    def begin_session(self) -> None:
        if self.session_counter == 0:
            self.handle.open()
        self.session_counter += 1

    def end_session(self) -> None:
        self.session_counter = max(self.session_counter - 1, 0)
        if self.session_counter == 0:
            self.handle.close()

    def read(self) -> MessagePayload:
        raise NotImplementedError

    def write(self, message_type: int, message_data: bytes) -> None:
        raise NotImplementedError

    def nfc_send(self, message_type: int, message_data: bytes) -> MessagePayload:
        raise NotImplementedError

    def ble_read(self) -> MessagePayload:
        raise NotImplementedError

    def write_ble(self, message_type: int, message_data: bytes):
        raise NotImplementedError


class ProtocolBasedTransport(Transport):
    """Transport that implements its communications through a Protocol.

    Intended as a base class for implementations that proxy their communication
    operations to a Protocol.
    """

    def __init__(self, protocol: Protocol) -> None:
        self.protocol = protocol

    def write(self, message_type: int, message_data: bytes) -> None:
        self.protocol.write(message_type, message_data)

    def read(self) -> MessagePayload:
        return self.protocol.read()

    def write_ble(self, message_type: int, message_data: bytes) -> None:
        self.protocol.write_ble(message_type, message_data)

    def send_nfc(self, message_type: int, message_data: bytes) -> MessagePayload:
        return self.protocol.nfc_send(message_type, message_data)

    def read_ble(self) -> MessagePayload:
        return self.protocol.ble_read()

    def begin_session(self) -> None:
        self.protocol.begin_session()

    def end_session(self) -> None:
        self.protocol.end_session()


class ProtocolV1(Protocol):
    """Protocol version 1. Currently (11/2018) in use on all Trezors.
    Does not understand sessions.
    """

    HEADER_LEN = struct.calcsize(">HL")

    def write(self, message_type: int, message_data: bytes) -> None:
        global PROCESS_REPORTER
        header = struct.pack(">HL", message_type, len(message_data))
        buffer = bytearray(b"##" + header + message_data)
        origin = len(buffer)
        while buffer:
            if PROCESS_REPORTER and origin >= 64:
                left = round(len(buffer) / origin, 2)
                PROCESS_REPORTER.publishProgress(int((1 - left) * 100))
                if len(buffer) <= 64:
                    PROCESS_REPORTER = None
                # Report ID, data padded to 63 bytes
            chunk = b"?" + buffer[: REPLEN - 1]
            chunk = chunk.ljust(REPLEN, b"\x00")
            self.handle.write_chunk(chunk)
            buffer = buffer[63:]

    def read(self) -> MessagePayload:
        buffer = bytearray()
        # Read header with first part of message data
        msg_type, datalen, first_chunk = self.read_first()
        buffer.extend(first_chunk)

        # Read the rest of the message
        while len(buffer) < datalen:
            buffer.extend(self.read_next())

        return msg_type, buffer[:datalen]

    def read_first(self) -> Tuple[int, int, bytes]:
        chunk = self.handle.read_chunk()
        if chunk[:3] != b"?##":
            raise RuntimeError("Unexpected magic characters")
        try:
            msg_type, datalen = struct.unpack(">HL", chunk[3: 3 + self.HEADER_LEN])
        except Exception:
            raise RuntimeError("Cannot parse header")

        data = chunk[3 + self.HEADER_LEN:]
        return msg_type, datalen, data

    def read_next(self) -> bytes:
        chunk = self.handle.read_chunk()
        if chunk[:1] != b"?":
            raise RuntimeError("Unexpected magic characters")
        return chunk[1:]

    def write_ble(self, message_type: int, message_data: bytes) -> None:
        global PROCESS_REPORTER
        header = struct.pack(">HL", message_type, len(message_data))
        buffer = bytearray(b"##" + header + message_data)
        origin = len(buffer)
        while buffer:
            if PROCESS_REPORTER and origin >= 64:
                left = round(len(buffer) / origin, 2)
                PROCESS_REPORTER.publishProgress(int((1 - left) * 100))
                if len(buffer) <= 64:
                    PROCESS_REPORTER = None
            # Report ID, data padded to 63 bytes
            waiting_packets = buffer[:189]
            send_packets = []
            while waiting_packets:
                chunk = b"?" + waiting_packets[: REPLEN - 1]
                chunk = chunk.ljust(REPLEN, b"\x00")
                send_packets.extend(chunk)
                waiting_packets = waiting_packets[63:]
            self.handle.write_chunk(bytes(send_packets))
            buffer = buffer[189:]

    def nfc_send(self, message_type: int, message_data: bytes) -> MessagePayload:
        global PROCESS_REPORTER, HTTP, OFFSET
        header = struct.pack(">HL", message_type, len(message_data))
        buffer = bytearray(b"##" + header + message_data)
        # split buffer into 64 bytes one package to send
        origin = len(buffer)
        if HTTP and OFFSET:
            origin = TOTAL
        while buffer:
            # used for android update progress bar
            if PROCESS_REPORTER and origin >= 64:
                left = round(len(buffer) / origin, 2)
                PROCESS_REPORTER.publishProgress(int((1 - left) * 100))
                if len(buffer) <= 64:
                    PROCESS_REPORTER = None
            # Report ID, data padded to 63 bytes
            waiting_packets = buffer[:2205]
            send_packets = bytearray()
            while waiting_packets:
                chunk = b"?" + waiting_packets[: REPLEN - 1]
                chunk = chunk.ljust(REPLEN, b"\x00")
                send_packets.extend(chunk)
                waiting_packets = waiting_packets[63:]
            print(f"send in nfc {bytes(send_packets).hex()}")
            response = self.handle.write_chunk_nfc(send_packets)
            if response == b'\x90\x00':
                buffer = buffer[2205:]
            else:
                print(f"unknown response {response}")
                raise BaseException("Unexpected response")
        print(f"send in nfc #**")
        response = b'#**'
        while response == b'#**':
            print(f"receive from nfc====={response}===")
            response = self.handle.write_chunk_nfc(bytearray(b'#**'))
        if response[:3] != b"?##":
            raise RuntimeError("Unexpected magic characters")
        try:
            msg_type, data_len = struct.unpack(">HL", response[3: 3 + self.HEADER_LEN])
        except Exception:
            raise RuntimeError("Cannot parse header")
        return msg_type, response[3 + self.HEADER_LEN:]

    def ble_read(self) -> MessagePayload:
        response = self.handle.read_ble()
        if response[:3] != b"?##":
            raise RuntimeError("Unexpected magic characters")
        try:
            msg_type, data_len = struct.unpack(">HL", response[3: 3 + self.HEADER_LEN])
        except Exception:
            raise RuntimeError(f"Cannot parse header")
        return msg_type, response[3 + self.HEADER_LEN:]
