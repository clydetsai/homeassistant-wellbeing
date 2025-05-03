"""Select platform for Wellbeing."""

import logging
import asyncio

from typing import cast

from homeassistant.components.humidifier import HumidifierEntity, HumidifierEntityFeature
from homeassistant.const import Platform

from . import WellbeingDataUpdateCoordinator
from .api import ApplianceHumidifier
from .api import OperationFunction
from .const import DOMAIN
from .entity import WellbeingEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup select platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    appliances = coordinator.data.get("appliances", None)

    if appliances is not None:
        for pnc_id, appliance in appliances.appliances.items():
            async_add_devices(
                [
                    WellbeingHumidifier(coordinator, entry, pnc_id, entity.entity_type, entity.attr)
                    for entity in appliance.entities
                    if entity.entity_type == Platform.HUMIDIFIER
                ]
            )


class WellbeingHumidifier(WellbeingEntity, HumidifierEntity):
    """wellbeing Humidifier class."""
    _attr_supported_features = (
        HumidifierEntityFeature.MODES
    )

    def __init__(self, coordinator, config_entry, pnc_id, entity_type, entity_attr):
        super().__init__(coordinator, config_entry, pnc_id, entity_type, entity_attr)
        self.current_humidity = self.get_appliance.get_entity(Platform.SENSOR, "sensorHumidity").state
        self.target_humidity = self.get_appliance.get_entity(Platform.SENSOR, "targetHumidity").state
        self.available_modes = ["AUTOMATIC", "MANUAL", "QUIET"]
        self.mode = self.get_entity.state


    @property
    def is_on(self):
        return self.get_appliance.get_entity(Platform.BINARY_SENSOR, "applianceState").state == "RUNNING"
    

    async def async_set_mode(self, mode: str) -> None:
        _LOGGER.debug(f"##async_set_mode")

    async def async_set_humidity(self, humidity: int) -> None:
        _LOGGER.debug(f"##async_set_humidity")
    
    async def async_turn_on(self, **kwargs) -> None:
        _LOGGER.debug(f"##async_turn_on")

    async def async_turn_off(self, **kwargs) -> None:
        _LOGGER.debug(f"##async_turn_off")
