from collections.abc import Callable
import datetime

from ..enums import BLECommandCode, DeviceLockWorkMode
from ..util import date_from_4bytes, date_to_4bytes, to_byte_array
from .device import UtecBleDevice, UtecBleRequest

STATUS_SETTLE_SECONDS = 2


def build_autolock_payload(seconds: int, door_sensor: bool, enabled: bool) -> bytes:
    """Build the three-byte SET_AUTOLOCK payload."""

    if not 0 <= seconds <= 0xFFFF:
        raise ValueError("Auto-lock duration must be between 0 and 65535 seconds.")
    if not enabled:
        return bytes(3)
    return to_byte_array(seconds, 2) + bytes([not door_sensor])


def parse_autolock_hex(value: str) -> bytes:
    """Parse a manually supplied auto-lock payload."""

    value = value.strip()
    if value.lower().startswith("0x"):
        value = value[2:]
    try:
        payload = bytes.fromhex(value)
    except ValueError as err:
        raise ValueError("Manual payload must be valid hex.") from err
    if not payload:
        raise ValueError("Manual payload cannot be empty.")
    return payload


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
            self.add_request(
                UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True)
            )
            self.add_request(
                UtecBleRequest(
                    BLECommandCode.UNLOCK,
                    auth_required=True,
                    delay_after=STATUS_SETTLE_SECONDS if update else 0,
                )
            )
            if update:
                self.add_request(UtecBleRequest(BLECommandCode.LOCK_STATUS))

        return await self.execute_requests(queue)

    async def async_lock(self, update: bool = True):
        def queue():
            self.add_request(
                UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True)
            )
            self.add_request(
                UtecBleRequest(
                    BLECommandCode.BOLT_LOCK,
                    auth_required=True,
                    delay_after=STATUS_SETTLE_SECONDS if update else 0,
                )
            )
            if update:
                self.add_request(UtecBleRequest(BLECommandCode.LOCK_STATUS))

        return await self.execute_requests(queue)

    async def async_reboot(self) -> bool:
        return await self.execute_requests(
            lambda: self.add_request(UtecBleRequest(BLECommandCode.REBOOT))
        )

    async def async_get_device_information(self) -> dict[str, dict[str, str]]:
        """Probe supported information without aborting after one failure."""

        commands = [BLECommandCode.ADMIN_LOGIN, BLECommandCode.LOCK_STATUS]
        if not self.capabilities.bt264:
            commands.extend(
                (BLECommandCode.GET_LOCK_STATUS, BLECommandCode.GET_BATTERY)
            )
        if self.capabilities.autolock:
            commands.append(BLECommandCode.GET_AUTOLOCK)
        if self.capabilities.mutemode:
            commands.append(BLECommandCode.GET_MUTE)
        if self.capabilities.havesn:
            commands.append(BLECommandCode.GET_SN)
        if not self.capabilities.bt264:
            commands.append(BLECommandCode.READ_TIME)
        if self.capabilities.doorsensor:
            commands.append(BLECommandCode.DOORSENSOR)

        self.calendar = None
        self.device_time_offset = None
        requests = [UtecBleRequest(command) for command in commands]

        def queue() -> None:
            for request in requests:
                self.add_request(request)

        await self.execute_requests(queue, continue_on_error=True)
        responses: dict[str, str] = {}
        errors: dict[str, str] = {}
        for request in requests:
            key = request.command.name.lower()
            if request.error:
                errors[key] = str(request.error)
            elif not request.response.success:
                errors[key] = "Rejected by lock"
            elif request.command != BLECommandCode.ADMIN_LOGIN:
                responses[key] = request.response.data.hex()
        return {"responses": responses, "errors": errors}

    async def async_set_device_time(
        self, device_time: datetime.datetime | Callable[[], datetime.datetime]
    ) -> dict:
        """Set the lock's local clock and attempt to read it back."""

        if isinstance(device_time, datetime.datetime):
            sent_time = device_time.replace(microsecond=0)
            write_data = date_to_4bytes(sent_time)
        else:
            sent_time = None

            def write_data() -> bytes:
                nonlocal sent_time
                sent_time = device_time().replace(microsecond=0)
                return date_to_4bytes(sent_time)

        login = UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True)
        write = UtecBleRequest(
            BLECommandCode.WRITE_TIME,
            data=write_data,
            delay_after=STATUS_SETTLE_SECONDS,
        )
        status = UtecBleRequest(BLECommandCode.LOCK_STATUS)

        def queue() -> None:
            for request in (login, write, status):
                self.add_request(request)

        self.calendar = None
        self.device_time_offset = None
        await self.execute_requests(queue)

        result = {
            "requested_time": sent_time.isoformat(),
            "payload": write.data.hex(),
            "status_response": status.response.data.hex(),
        }
        if write.response.is_valid:
            result["write_response"] = write.response.data.hex()
        try:
            read_back = date_from_4bytes(status.response.data[5:9])
        except ValueError as err:
            result["read_back_error"] = str(err)
        else:
            if read_back:
                result["read_back"] = read_back.isoformat()
            else:
                result["read_back_error"] = "LOCK_STATUS did not include device time"
        return result

    async def async_set_workmode(self, mode: DeviceLockWorkMode):
        def queue():
            self.add_request(
                UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True)
            )
            command = (
                BLECommandCode.SET_LOCK_STATUS
                if self.capabilities.bt264
                else BLECommandCode.SET_WORK_MODE
            )
            self.add_request(UtecBleRequest(command, data=bytes([mode.value])))

        return await self.execute_requests(queue)

    async def async_set_autolock(self, payload: bytes):
        if not self.capabilities.autolock:
            raise ValueError(f"{self.name} does not support auto-lock.")
        if not payload:
            raise ValueError("Auto-lock payload cannot be empty.")

        def queue():
            self.add_request(
                UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True)
            )
            self.add_request(UtecBleRequest(BLECommandCode.SET_AUTOLOCK, data=payload))

        return await self.execute_requests(queue)

    async def async_update_status(self, skip_if_busy: bool = False):
        self.debug("(%s) %s - Updating lock data...", self.mac_uuid, self.name)

        def queue():
            self.add_request(
                UtecBleRequest(BLECommandCode.ADMIN_LOGIN, auth_required=True)
            )
            self.add_request(UtecBleRequest(BLECommandCode.LOCK_STATUS))
            if not self.capabilities.bt264:
                self.add_request(UtecBleRequest(BLECommandCode.GET_LOCK_STATUS))
                self.add_request(UtecBleRequest(BLECommandCode.GET_BATTERY))
                if self.capabilities.mutemode:
                    self.add_request(UtecBleRequest(BLECommandCode.GET_MUTE))
            if self.capabilities.autolock:
                self.add_request(UtecBleRequest(BLECommandCode.GET_AUTOLOCK))

        updated = await self.execute_requests(queue, skip_if_busy)
        if updated:
            self.debug("(%s) %s - Update Successful.", self.mac_uuid, self.name)
        return updated
