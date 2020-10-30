import binascii
import time

from typing import Iterable

from .protocol import ProtocolBasedTransport, Handle, ProtocolV1

from rubicon.objc import ObjCClass, ObjCInstance

WRITE_SUCCESS = True
IS_CANCEL = False


class BlueToothIosHandler(Handle):
    BLE = None  # type: ObjCInstance
    BLE_DEVICE = None  # type: str
    BLE_ADDRESS = ''  # type: str
    CALL_BACK = None  # type: ObjCInstance
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
        while not IS_CANCEL and BlueToothIosTransport.ENABLED:
            # print(f"ble write in ===={threading.currentThread().ident}")
            wait_seconds = int(time.time()) - start
            if WRITE_SUCCESS and not IS_CANCEL:
                WRITE_SUCCESS = False
                success = cls.BLE.write(cls.BLE_DEVICE, chunks, cls.CALL_BACK)
                if success:
                    return
                else:
                    raise BaseException("send failed")
            elif wait_seconds >= 5:
                raise BaseException("waiting send timeout")
            else:
                time.sleep(0.001)
        if IS_CANCEL or not BlueToothIosTransport.ENABLED:
            raise BaseException("user cancel")

    @classmethod
    def read_ble(cls) -> bytes:
        global IS_CANCEL
        start = int(time.time())
        IS_CANCEL = False
        while not IS_CANCEL and BlueToothIosTransport.ENABLED:
            wait_seconds = int(time.time()) - start
            if cls.RESPONSE and not IS_CANCEL:
                new_response = bytes(binascii.unhexlify(cls.RESPONSE))
                cls.RESPONSE = ''
                return new_response
            elif wait_seconds >= 120:
                raise BaseException("read ble response timeout")
            else:
                time.sleep(0.1)
        if IS_CANCEL or not BlueToothIosTransport.ENABLED:
            cls.RESPONSE = ''
            raise BaseException("user cancel")


class BlueToothIosTransport(ProtocolBasedTransport):
    PATH_PREFIX = "bluetooth_ios"
    ENABLED = True

    def __init__(
            self, device: str, handle: BlueToothIosHandler = None) -> None:
        assert handle is not None, "bluetooth handler can not be None"
        self.device = device
        self.handle = handle
        super().__init__(protocol=ProtocolV1(handle))

    def get_path(self) -> str:
        return self.device

    @classmethod
    def enumerate(cls) -> Iterable["BlueToothIosTransport"]:
        return [BlueToothIosTransport(cls.PATH_PREFIX, BlueToothIosHandler())]
