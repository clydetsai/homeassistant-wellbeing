"""Select platform for Wellbeing."""

import logging
import asyncio

from typing import cast

from homeassistant.components.humidifier import HumidifierEntity, HumidifierEntityFeature, HumidifierAction
from homeassistant.const import Platform

from . import WellbeingDataUpdateCoordinator
from .api import ApplianceHumidifier
from .api import OperationFunction
from .api import WorkMode, OperationFunction
from .const import DOMAIN
from .entity import WellbeingEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup select platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    appliances = coordinator.data.get("appliances", None)

    humidifier_entities = []

    if appliances is not None:
        for pnc_id, appliance in appliances.appliances.items():
            for entity in appliance.entities:
                if entity.entity_type == Platform.HUMIDIFIER:
                    h = WellbeingHumidifier(coordinator, entry, pnc_id, entity.entity_type, entity.attr)
                    async_add_devices([h])
                    humidifier_entities.append(h)

    hass.data.setdefault(DOMAIN, {})["humidifier_entities"] = humidifier_entities


class WellbeingHumidifier(WellbeingEntity, HumidifierEntity):
    """wellbeing Humidifier class."""
    _attr_supported_features = (
        HumidifierEntityFeature.MODES
    )

    def __init__(self, coordinator, config_entry, pnc_id, entity_type, entity_attr):
        super().__init__(coordinator, config_entry, pnc_id, entity_type, entity_attr)
        self.current_humidity = self.get_appliance.get_entity(Platform.SENSOR, "sensorHumidity").state
        self.max_humidity = 85
        self.min_humidity = 30
        self.available_modes = [WorkMode.AUTOMATIC, WorkMode.MANUAL, WorkMode.QUIET]
        self.mode = self.get_entity.state # one of mode from available_modes
        self._nexttime_target_humidity = 45
        self._target_humidity = self.get_appliance.get_entity(Platform.SENSOR, "targetHumidity").state
        self._action = HumidifierAction.OFF

    @property
    def target_humidity(self):
        _LOGGER.debug(f"##WellbeingHumidifier.checking target humidity: published_target = {self.get_appliance.get_entity(Platform.SENSOR, "targetHumidity").state}")
        _LOGGER.debug(f"##WellbeingHumidifier.checking target humidity: current mode = {self.mode}")
        _LOGGER.debug(f"##WellbeingHumidifier.checking target humidity: current function = {self.get_appliance.get_entity(Platform.SELECT, "mode").state}")
        self.current_humidity = self.get_appliance.get_entity(Platform.SENSOR, "sensorHumidity").state
        published_targetHumidity = self.get_appliance.get_entity(Platform.SENSOR, "targetHumidity").state
        if self.mode != WorkMode.MANUAL and published_targetHumidity != self._target_humidity:
            self._target_humidity = 45
        #if self.get_appliance.get_entity(Platform.SELECT, "mode").state == OperationFunction.CONTINUOUS:
        #    self._target_humidity = 30
        return self._target_humidity

    @property
    def action(self):
        if self.get_appliance.get_entity(Platform.BINARY_SENSOR, "applianceState").state:
            if self.get_appliance.get_entity(Platform.SELECT, "mode").state == OperationFunction.PURIFY:
                self._action = HumidifierAction.IDLE
            else:
                self._action = HumidifierAction.DRYING
        else:
            self._action = HumidifierAction.OFF
        return self._action

    @property
    def is_on(self):
        # entity of applianceState already return true or false
        return self.get_appliance.get_entity(Platform.BINARY_SENSOR, "applianceState").state

    
    async def async_set_mode(self, mode: str) -> None:
        #_LOGGER.debug(f"##WellbeingHumidifier.async_set_mode(): set mode from {self.mode} to {targetMode}")
        _LOGGER.debug(f"##WellbeingHumidifier.async_set_mode(): set mode")
        # when switch to AUTO/QUIET, default target is 45
        if mode != WorkMode.MANUAL:
            self._target_humidity = 45
        else: # when switch to MANUAL, call back _nexttime_target_humidity
            self._target_humidity = self._nexttime_target_humidity

        await self.api.set_work_mode(self.pnc_id, WorkMode(mode))
        self.mode = mode
        self.async_write_ha_state()
        await asyncio.sleep(10)
        await self.coordinator.async_request_refresh()


    async def async_set_humidity(self, humidity: int, functionFlag: int = 0) -> None:
        _LOGGER.debug(f"##WellbeingHumidifier.async_set_humidity():")
        if self.is_on == False:
            _LOGGER.debug(f"##async_set_humidity(): can not set humidity when switched off")
            return
        if humidity >= self.current_humidity:
            _LOGGER.debug(f"##async_set_humidity(): targetHumidity too high")
            return
        elif humidity < self.min_humidity or humidity > self.max_humidity:
            _LOGGER.debug(f"##async_set_humidity(): targetHumidity out of range")
            return

        self._nexttime_target_humidity = humidity

        #if(self.get_appliance.get_entity(Platform.SELECT, "mode").state == OperationFunction.CONTINUOUS):
        if functionFlag == 1:
            _LOGGER.debug(f"##async_set_humidity(): funciton changing, set to {humidity}")
            self._target_humidity = humidity
            #self.async_write_ha_state()
            return

        # change to MANUAL when current mode is not MANUAL
        if self.mode != WorkMode.MANUAL:
            _LOGGER.debug(f"##async_set_humidity(): not in MANUAL, set to MANUAL")
            await self.async_set_mode(WorkMode.MANUAL)


        await self.api.set_target_humidity(self.pnc_id, humidity)
        self._target_humidity = humidity
        self.async_write_ha_state()
        await asyncio.sleep(10)
        await self.coordinator.async_request_refresh()


    async def async_turn_on(self, **kwargs) -> None:
        _LOGGER.debug(f"##WellbeingHumidifier.async_turn_on(): turn on")
        await self.api.set_work_mode(self.pnc_id, WorkMode.POWERON)
        self.async_write_ha_state()
        await asyncio.sleep(10)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        _LOGGER.debug(f"##WellbeingHumidifier.async_turn_off(): turn off")
        await self.api.set_work_mode(self.pnc_id, WorkMode.OFF)
        self.async_write_ha_state()
        await asyncio.sleep(10)
        await self.coordinator.async_request_refresh()
