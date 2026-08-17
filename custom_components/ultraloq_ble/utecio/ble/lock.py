import datetime

from ..enums import BLECommandCode, DeviceLockWorkMode
from ..util import to_byte_array
from .device import UtecBleDevice, UtecBleRequest


class UtecBleLock(UtecBleDevice):
    def __init__(
        self,
        uid: str,
        password: str,
        mac_uuid: str,
        device_name: str,
        wurx_uuid: str = "",
        device_model: str = "",
    ):
        super().__init__(
            uid=uid,
            password=password,
            mac_uuid=mac_uuid,
            wurx_uuid=wurx_uuid,
            device_name=device_name,
            device_model=device_model,
        )

    async def async_unlock(self, update: bool = True):
        def queue():
            self.add_request(UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True))
            self.add_request(UtecBleRequest(BLECommandCode.UNLOCK, auth_required=True))
            if update:
                self.add_request(UtecBleRequest(BLECommandCode.LOCK_STATUS))

        return await self.execute_requests(queue)

    async def async_lock(self, update: bool = True):
        def queue():
            self.add_request(UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True))
            self.add_request(UtecBleRequest(BLECommandCode.BOLT_LOCK, auth_required=True))
            if update:
                self.add_request(UtecBleRequest(BLECommandCode.LOCK_STATUS))

        return await self.execute_requests(queue)

    async def async_reboot(self) -> bool:
        return await self.execute_requests(
            lambda: self.add_request(UtecBleRequest(BLECommandCode.REBOOT))
        )

    async def async_set_workmode(self, mode: DeviceLockWorkMode):
        def queue():
            self.add_request(UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True))
            command = (
                BLECommandCode.SET_LOCK_STATUS
                if self.capabilities.bt264
                else BLECommandCode.SET_WORK_MODE
            )
            self.add_request(UtecBleRequest(command, data=bytes([mode.value])))

        return await self.execute_requests(queue)

    async def async_set_autolock(self, seconds: int):
        def queue():
            if not self.capabilities.autolock:
                return
            self.add_request(
                UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True)
            )
            self.add_request(
                UtecBleRequest(
                    BLECommandCode.SET_AUTOLOCK,
                    data=to_byte_array(seconds, 2) + bytes([0]),
                )
            )

        return await self.execute_requests(queue)

    async def async_update_status(self, skip_if_busy: bool = False):
        self.debug("(%s) %s - Updating lock data...", self.mac_uuid, self.name)

        def queue():
            self.add_request(UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True))
            self.add_request(UtecBleRequest(BLECommandCode.LOCK_STATUS))
            if not self.capabilities.bt264:
                self.add_request(UtecBleRequest(BLECommandCode.GET_LOCK_STATUS))
                self.add_request(UtecBleRequest(BLECommandCode.GET_BATTERY))
                self.add_request(UtecBleRequest(BLECommandCode.GET_MUTE))
            if self.capabilities.autolock:
                self.add_request(UtecBleRequest(BLECommandCode.GET_AUTOLOCK))

        updated = await self.execute_requests(queue, skip_if_busy)
        if updated:
            self.debug("(%s) %s - Update Successful.", self.mac_uuid, self.name)
        return updated
