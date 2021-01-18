import os
import time

from threading import Timer
from .transport import protocol
from electrum.util import print_stderr, raw_input, _logger

IS_ANDROID = True
UI_HANDLER = None
if "iOS_DATA" in os.environ:
    from rubicon.objc import ObjCClass
    UI_HANDLER = ObjCClass("OKBlueManager")
    IS_ANDROID = False
    TAG = "HardwareNotifications"
elif "ANDROID_DATA" in os.environ:
    from android.os import Handler


class CustomerUI:
    def __init__(self):
        pass

    pin = ''  # type: str
    passphrase = ''  # type: str
    user_cancel = 0
    pass_state = 0
    handler = None
    if not IS_ANDROID:
            handler = UI_HANDLER.sharedInstance().getNotificationCenter()

    @classmethod
    def set_pin(cls, pin: str):
        cls.pin = pin

    # this method must be classmethod in order to keep  Memory consistency
    @classmethod
    def get_pin(cls, code, show_strength=False) -> str:
        cls.code = code
        cls.user_cancel = 0
        cls.pin = ''
        if cls.handler:
            if code == '2':
                if IS_ANDROID:
                    cls.handler.sendEmptyMessage(2)
                else:
                    cls.handler.postNotificationName_object_(TAG, "2")
            elif code == '1':
                if IS_ANDROID:
                    cls.handler.sendEmptyMessage(1)
                else:
                    cls.handler.postNotificationName_object_(TAG, "1")
        start = int(time.time())
        while True:
            wait_seconds = int(time.time()) - start
            if cls.user_cancel:
                cls.user_cancel = 0
                raise BaseException("user cancel")
            elif cls.pin != '':
                pin_current = cls.pin
                cls.pin = ''
                return pin_current
            elif wait_seconds >= 60:
                raise BaseException("waiting pin timeout")
            else:
                time.sleep(0.0001)

    @classmethod
    def set_pass_state(cls, state):
        cls.pass_state = state

    @classmethod
    def get_pass_state(cls):
        pass_state_current = cls.pass_state
        cls.pass_state = 0
        return pass_state_current

    @classmethod
    def get_state(cls):
        state_current = cls.state
        cls.state = 0
        return state_current

    @classmethod
    def get_passphrase(cls, msg, confirm=None) -> str:
        cls.code = msg
        cls.passphrase = ''
        cls.user_cancel = 0
        if cls.pass_state == 0:
            return ''
        cls.pass_state = 0
        if cls.handler:
            if msg == "6":
                if IS_ANDROID:
                    cls.handler.sendEmptyMessage(6)
                else:
                    cls.handler.postNotificationName_object_(TAG, "6")
            elif msg == "3":
                if IS_ANDROID:
                    cls.handler.sendEmptyMessage(3)
                else:
                    cls.handler.postNotificationName_object_(TAG, "3")
        start = int(time.time())
        while True:
            wait_seconds = int(time.time()) - start
            if cls.user_cancel:
                cls.user_cancel = 0
                raise BaseException("user cancel")
            elif cls.passphrase != '':
                passphrase_current = cls.passphrase
                cls.passphrase = ''
                return passphrase_current
            elif wait_seconds >= 60:
                raise BaseException("waiting passphrase timeout")
            else:
                time.sleep(0.0001)
            #

    @classmethod
    def button_request(cls, code):
        if code == 9:
            timer = Timer(1.0, lambda: protocol.notify())
            timer.start()
            return
        if IS_ANDROID:
            cls.handler.sendEmptyMessage(code)
        else:
            cls.handler.postNotificationName_object_(TAG, f"{code}")
        return

    def finished(self):
        return

    def show_message(self, msg, on_cancel=None):
        return

    def prompt_auth(self, msg):
        import getpass
        print_stderr(msg)
        response = getpass.getpass('')
        if len(response) == 0:
            return None
        return response

    def yes_no_question(self, msg):
        print_stderr(msg)
        return False

    def stop(self):
        pass

    def show_error(self, msg, blocking=False):
        print_stderr(msg)

    def update_status(self, b):
        _logger.info(f'hw device status {b}')
