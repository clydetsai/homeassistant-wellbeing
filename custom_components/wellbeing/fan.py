"""Sensor platform for Wellbeing."""

import asyncio
import logging
import math

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.const import Platform
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage

from . import WellbeingDataUpdateCoordinator
from .api import Model

from .api import WorkMode
from .const import DOMAIN
from .entity import WellbeingEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    appliances = coordinator.data.get("appliances", None)

    if appliances is not None:
        for pnc_id, appliance in appliances.appliances.items():
            async_add_devices(
                [
                    WellbeingFan(coordinator, entry, pnc_id, entity.entity_type, entity.attr)
                    for entity in appliance.entities
                    if entity.entity_type == Platform.FAN
                ]
            )


class WellbeingFan(WellbeingEntity, FanEntity):
    """wellbeing Sensor class."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE | FanEntityFeature.TURN_OFF | FanEntityFeature.TURN_ON
    )

    def __init__(self, coordinator: WellbeingDataUpdateCoordinator, config_entry, pnc_id, entity_type, entity_attr):
        super().__init__(coordinator, config_entry, pnc_id, entity_type, entity_attr)
        self._preset_mode = self.get_appliance.mode
        self._speed = self.get_entity.state

    @property
    def _speed_range(self) -> tuple[int, int]:
        return self.get_appliance.speed_range

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return self._speed_range[1]

    @property
    def percentage(self):
        """Return the current speed percentage."""
        if self._preset_mode == WorkMode.OFF:
            speed = 0
        else:
            if self.get_appliance.model == Model.UltimateHome700:
                _LOGGER.debug(f"##checking percentage...")
                _LOGGER.debug(f"##self.get_appliance.get_entity(Platform.SENSOR, 'fanSpeedState').state={self.get_appliance.get_entity(Platform.SENSOR, "fanSpeedState").state}")
                _LOGGER.debug(f"##fanSpeedSetting={self.get_entity.state}")
                currentFanSpeed = self.get_appliance.get_entity(Platform.SENSOR, "fanSpeedState").state
                if currentFanSpeed == "LOW":
                    speed = 1
                elif currentFanSpeed == "MIDDLE":
                    speed = 2
                elif currentFanSpeed == "HIGH":
                    speed = 3
                else:
                    _LOGGER.debug(f"##unknow currentFanSpeed={currentFanSpeed}")
                    speed = 1
                

        percentage = ranged_value_to_percentage(self._speed_range, speed)
        _LOGGER.debug(f"percentage - speed: {speed} percentage: {percentage}")
        return percentage

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        self._speed = math.ceil(percentage_to_ranged_value(self._speed_range, percentage))
        
        if self.get_appliance.model == Model.UltimateHome700:
            _LOGGER.debug(f"##setting percentage...")
            _LOGGER.debug(f"##self.speed: {self._speed} percentage: {percentage}")
            _LOGGER.debug(f"##fanSpeedSetting: {self.get_entity.state}")

        self.get_entity.clear_state()
        self.async_write_ha_state()

        _LOGGER.debug(f"async_set_percentage - speed: {self._speed} percentage: {percentage}")

        if percentage == 0:
            await self.async_turn_off()
            return

        is_manual = self.preset_mode == WorkMode.MANUAL
        # make sure manual is set before setting speed
        if not is_manual:
            await self.async_set_preset_mode(WorkMode.MANUAL)

        await self.api.set_fan_speed(self.pnc_id, self._speed)

        self.async_write_ha_state()
        await asyncio.sleep(10)
        await self.coordinator.async_request_refresh()

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., auto, smart, interval, favorite."""
        return (
            self._preset_mode.value
            if self.get_appliance.mode.value is WorkMode.UNDEFINED.value
            else self.get_appliance.mode.value
        )

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return self.get_appliance.preset_modes

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        self._valid_preset_mode_or_raise(preset_mode)
        self._preset_mode = WorkMode(preset_mode)

        self.get_appliance.set_mode(self._preset_mode)
        self.async_write_ha_state()
        await self.api.set_work_mode(self.pnc_id, self._preset_mode)
        await asyncio.sleep(10)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self):
        if self.get_appliance.model == Model.UltimateHome700:
            currentState = self.get_appliance.get_entity(Platform.BINARY_SENSOR, "applianceState").state
            return currentState
        return self.preset_mode != WorkMode.OFF

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs) -> None:
        if self.get_appliance.model == Model.UltimateHome700:
            _LOGGER.debug(f"##turn on...")
            await self.api.set_work_mode(self.pnc_id, WorkMode.POWERON)
        else:
            self._preset_mode = self.get_appliance.work_mode_from_preset_mode(preset_mode)

            # Handle incorrect percentage
            if percentage is not None and isinstance(percentage, str):
                try:
                    percentage = int(percentage)
                except ValueError:
                    _LOGGER.error(f"Invalid percentage value: {percentage}")
                    return

            # Proceed with the provided or default percentage
            self._speed = math.floor(percentage_to_ranged_value(self._speed_range, percentage or 10))
            self.get_appliance.set_mode(self._preset_mode)
            self.async_write_ha_state()
            
            await self.api.set_work_mode(self.pnc_id, self._preset_mode)

            if self._preset_mode != WorkMode.AUTO:
                await self.api.set_fan_speed(self.pnc_id, self._speed)

        await asyncio.sleep(10)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        if self.get_appliance.model == Model.UltimateHome700:
            _LOGGER.debug(f"##turn off...")
        else:
            self._preset_mode = WorkMode.OFF
            self._speed = 0
            self.get_appliance.set_mode(self._preset_mode)
            self.async_write_ha_state()

        await self.api.set_work_mode(self.pnc_id, WorkMode.OFF)
        await asyncio.sleep(10)
        await self.coordinator.async_request_refresh()
