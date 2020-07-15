#####  BLE 、NFC 说明文档
- 开发思路
	
	- 借助`chaquo`混合编程框架，把`Android`中的`BLE`、`NFC` 、`USB`的**操作句柄**传入到`Python`代码中，这样既可以兼顾复用`Trezor`中的数据处理逻辑和使用`Android`原生的硬件接口，还避免了在`Python`操作手机硬件的复杂性。
	
- 开发原则： 

   - 不损害现有功能
   - 尽量只做新增、不做修改

- 具体实现 
   - `NFC`检测、开启前台调度这些功能放在`Android`中来做，因为`Android`中有现成的接口可以用，数据处理交给`Python`，通讯方面，具体的实现就是将`Android`中的`NFC`操作句柄`IsoDep`和硬件标识`Tag`传入`Python`中。

       ```python
         # nfc.py 代码片段
         try
             from android.nfc import NfcAdapter
             from android.nfc.tech import IsoDep
             from android.nfc import Tag
             from java import cast
         except Exception as e:
             LOG.warning("NFC transport is Unavailable: {}".format(e))
         class NFCHandle(Handle):
             device = None  # type:  Tag
         
             def __init__(self) -> None:
                 self.device = cast(Tag, NFCHandle.device)
                 self.handle = None  # type: Optional[IsoDep]
       ```
   - `BLE`使用了开源库[Android-BLE](https://github.com/aicareles/Android-BLE),设备扫描、连接使用`Android`原生接口来做，把数据操作的句柄传入`Python`

       ```python
       # bluetooth.py 代码片段
       from cn.com.heaton.blelibrary.ble.callback import BleWriteCallback
       from cn.com.heaton.blelibrary.ble import Ble
       from cn.com.heaton.blelibrary.ble.model import BleDevice
       
       class BlueToothHandler(Handle):
           BLE = None  # type: Ble
           BLE_DEVICE = None # type: BleDevice
           BLE_ADDRESS = ""  # type: str
           CALL_BACK = None  # type: BleWriteCallback
       ```


   - `USB` 使用`Android`原生的接口开发，思路与上面类似.

     ```python
     INTERFACE = 0
     ENDPOINT = 1
     DEBUG_INTERFACE = 1
     DEBUG_ENDPOINT = 2
     Timeout = 100
     forceClaim = True
     USB_Manager = None
     USB_DEVICE = None
     RESPONSE = ByteBuffer.allocate(64)
     
     class AndroidUsbHandle(Handle):
     
         def __init__(self) -> None:
             self.device = USB_DEVICE  # type: UsbDevice
             self.manger = USB_Manager  # type: UsbManager
             self.interface = None  # type: UsbInterface
             self.endpoint_in = None  # type: UsbEndpoint
             self.endpoint_out = None  # type: UsbEndpoint
             self.handle = None  # type: UsbDeviceConnection
     
     ```

     

