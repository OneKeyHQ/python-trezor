import binascii
import time

from typing import Iterable, Optional, cast

from .protocol import ProtocolBasedTransport, Handle, ProtocolV1
from cn.com.heaton.blelibrary.ble.callback import BleWriteCallback
from cn.com.heaton.blelibrary.ble import Ble
from cn.com.heaton.blelibrary.ble.model import BleDevice
from electrum.i18n import _
import threading

WRITE_SUCCESS = True
IS_CANCEL = False
lock = threading.RLock()


class BlueToothHandler(Handle):
    BLE = None  # type: Ble
    BLE_DEVICE = None  # type: BleDevice
    BLE_ADDRESS = ''  # type: str
    CALL_BACK = None  # type: BleWriteCallback
    RESPONSE = ''  # type: str
    WRITE_TIMEOUT = 5
    READ_TIMEOUT = 120

    def __init__(self) -> None:
        pass

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    @classmethod
    def set_cancel_flag(cls) -> None:
        global IS_CANCEL
        with lock:
            IS_CANCEL = True

    @classmethod
    def set_write_success_flag(cls) -> None:
        global WRITE_SUCCESS
        with lock:
            WRITE_SUCCESS = True

    @classmethod
    def set_response(cls, response: str) -> None:
        with lock:
            cls.RESPONSE = response

    @classmethod
    def write_chunk(cls, chunk: bytes) -> None:
        global WRITE_SUCCESS, IS_CANCEL
        assert cls.BLE is not None, _("Bluetooth device not available")
        chunks = binascii.unhexlify(bytes(chunk).hex())
        cls.RESPONSE = ''
        IS_CANCEL = False
        start = int(time.time())
        while not IS_CANCEL:
            wait_seconds = int(time.time()) - start
            with lock:
                if WRITE_SUCCESS and not IS_CANCEL:
                    success = cls.BLE.write(cls.BLE_DEVICE, chunks, cls.CALL_BACK)
                    if success:
                        WRITE_SUCCESS = False
                        return
                    else:
                        raise BaseException("send failed")
                elif wait_seconds >= cls.WRITE_TIMEOUT:
                    WRITE_SUCCESS = True
                    raise BaseException(_("Waiting for send timeout"))
                else:
                    time.sleep(0.001)
        if IS_CANCEL:
            raise BaseException("user cancel")

    @classmethod
    def read_ble(cls) -> bytes:
        global IS_CANCEL
        start = int(time.time())
        IS_CANCEL = False
        while not IS_CANCEL:
            wait_seconds = int(time.time()) - start
            with lock:
                if cls.RESPONSE and not IS_CANCEL:
                    new_response = bytes(binascii.unhexlify(cls.RESPONSE))
                    cls.RESPONSE = ''
                    return new_response
                elif wait_seconds >= cls.READ_TIMEOUT:
                    raise BaseException("read ble response timeout")
                else:
                    time.sleep(0.1)
        if IS_CANCEL:
            cls.RESPONSE = ''
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
