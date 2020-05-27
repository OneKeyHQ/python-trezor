import time

import logging
from typing import Iterable, Optional
from .protocol import ProtocolBasedTransport, ProtocolV1, Handle, event
from java.io import IOException
import binascii

LOG = logging.getLogger(__name__)

try:
    from android.nfc import NfcAdapter
    from android.nfc.tech import IsoDep
    from android.nfc import Tag
    from java import cast
except Exception as e:
    LOG.warning("NFC transport is Unavailable: {}".format(e))

IS_CANCEL = False

class NFCHandle(Handle):
    device = None  # type:  Tag
    handle = None

    def __init__(self) -> None:
        pass

    @classmethod
    def open(cls) -> None:
        if cls.device is not None:
            cls.handle = IsoDep.get(cls.device)
            try:
                cls.handle.setTimeout(5000)
                cls.handle.connect()
            except IOException as e:
                LOG.warning(f"NFC handler open exception {e.getMessage()}")
                raise BaseException(e)

    @classmethod
    def close(cls) -> None:
        if cls.handle is not None:
            cls.handle.close()
            cls.handle = None

    @classmethod
    def write_chunk_nfc(cls, chunk: bytearray) -> bytes:
        assert cls.handle is not None, "NFC handler is None"
        global IS_CANCEL
        response = []
        chunks = binascii.unhexlify(bytes(chunk).hex())
        count = 0
        # success = False
        IS_CANCEL = False
        import threading
        # while count < 3 and not success and not IS_CANCEL and NFCTransport.ENABLED:
        while count < 3 and not IS_CANCEL and NFCTransport.ENABLED:
            print(f"nfc write in ===={threading.currentThread().ident}")
            try:
                if not IS_CANCEL:
                    response = bytes(cls.handle.transceive(chunks))
                    # success = True
                    return response
            except IOException as e:
                if count < 2:
                    count = count + 1
                    print(f"send in nfc =====retry: {count}===={e.getMessage()}")
                    time.sleep(0.01)
                else:
                    print(f"fnc waiting touch, is_cancel== {IS_CANCEL}")
                    event.wait(10)
            finally:
                if event.is_set():
                    event.clear()
        if not response:
            raise BaseException("user cancel")
        # return response


class NFCTransport(ProtocolBasedTransport):
    """
    """

    PATH_PREFIX = "nfc"
    ENABLED = True

    def __init__(
            self, device: str, handle: NFCHandle = None) -> None:
        assert handle is not None, "nfc handler can not be None"
        self.device = device
        self.handle = handle
        super().__init__(protocol=ProtocolV1(handle))

    def get_path(self) -> str:
        return self.device

    @classmethod
    def enumerate(cls) -> Iterable["NFCTransport"]:
        return [NFCTransport(cls.PATH_PREFIX, NFCHandle())]
