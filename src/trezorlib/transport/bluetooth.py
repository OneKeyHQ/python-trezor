import binascii
import time

from typing import Iterable, Optional, cast

from .protocol import ProtocolBasedTransport, Handle, ProtocolV1
from cn.com.heaton.blelibrary.ble.callback import BleWriteCallback
from cn.com.heaton.blelibrary.ble import Ble
from cn.com.heaton.blelibrary.ble.model import BleDevice

WRITE_SUCCESS = True
IS_CANCEL = False


class BlueToothHandler(Handle):
    BLE = None  # type: Ble
    BLE_DEVICE = None  # type: BleDevice
    BLE_ADDRESS = ''  # type: str
    CALL_BACK = None  # type: BleWriteCallback
    RESPONSE = ''  # type: str

    def __init__(self) -> None:
        pass

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    @classmethod
    def write_chunk(cls, chunk: bytes) -> None:
        global WRITE_SUCCESS, IS_CANCEL
        assert cls.BLE is not None, "the bluetooth device is not available"
        chunks = binascii.unhexlify(bytes(chunk).hex())
        cls.RESPONSE = ''
        IS_CANCEL = False
        start = int(time.time())
        import threading
        while True and not IS_CANCEL and BlueToothTransport.ENABLED:
            print(f"ble write in ===={threading.currentThread().ident}")
            wait_seconds = int(time.time()) - start
            if WRITE_SUCCESS:
                WRITE_SUCCESS = False
                success = cls.BLE.write(cls.BLE_DEVICE, chunks, cls.CALL_BACK)
                if success:
                    return
                else:
                    raise BaseException("send failed")
            elif wait_seconds >= 5:
                raise BaseException("waiting notify success timeout")
            else:
                time.sleep(0.001)
        if IS_CANCEL or not BlueToothTransport.ENABLED:
            raise BaseException("user cancel")

    @classmethod
    def read_ble(cls) -> bytes:
        global IS_CANCEL
        start = int(time.time())
        IS_CANCEL = False
        import threading
        while True and not IS_CANCEL and BlueToothTransport.ENABLED:
            print(f"ble read in ===={threading.currentThread().ident}")
            wait_seconds = int(time.time()) - start
            if cls.RESPONSE:
                new_response = bytes(binascii.unhexlify(cls.RESPONSE))
                cls.RESPONSE = ''
                return new_response
            elif wait_seconds >= 30:
                raise BaseException("read ble response timeout")
            else:
                time.sleep(0.01)
        if IS_CANCEL or not BlueToothTransport.ENABLED:
            raise BaseException("user cancel")


class BlueToothTransport(ProtocolBasedTransport):
    PATH_PREFIX = "bluetooth"
    ENABLED = True

    def __init__(
            self, device: str, handle: BlueToothHandler = None) -> None:
        assert handle is not None, "bluetooth handler can not be None"
        self.device = device
        self.handle = handle
        super().__init__(protocol=ProtocolV1(handle))

    def get_path(self) -> str:
        return self.device

    @classmethod
    def enumerate(cls) -> Iterable["BlueToothTransport"]:
        return [BlueToothTransport(cls.PATH_PREFIX, BlueToothHandler())]
