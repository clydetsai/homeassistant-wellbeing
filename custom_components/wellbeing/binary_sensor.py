"""Binary sensor platform for Wellbeing."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import Platform

from .const import DOMAIN
from .entity import WellbeingEntity
import logging
import asyncio
_LOGGER: logging.Logger = logging.getLogger(__package__)

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    appliances = coordinator.data.get("appliances", None)

    capabilities = ["cleanAirMode", "uiLockMode", "verticalSwing", "displayLight"]

    if appliances is not None:
        for pnc_id, appliance in appliances.appliances.items():
            async_add_devices(
                [
                    WellbeingBinarySensor(coordinator, entry, pnc_id, entity.entity_type, entity.attr)
                    for entity in appliance.entities
                    if entity.entity_type == Platform.BINARY_SENSOR and entity.attr not in capabilities
                ]
            )


class WellbeingBinarySensor(WellbeingEntity, BinarySensorEntity):
    """wellbeing binary_sensor class."""

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.get_entity.state
