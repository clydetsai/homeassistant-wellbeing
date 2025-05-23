"""Sensor platform for Wellbeing."""

from typing import cast

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import Platform

from .api import ApplianceSensor
from .const import DOMAIN
from .entity import WellbeingEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    appliances = coordinator.data.get("appliances", None)

    if appliances is not None:
        for pnc_id, appliance in appliances.appliances.items():
            async_add_devices(
                [
                    WellbeingSensor(coordinator, entry, pnc_id, entity.entity_type, entity.attr, entity.options)
                    for entity in appliance.entities
                    if entity.entity_type == Platform.SENSOR
                ]
            )


class WellbeingSensor(WellbeingEntity, SensorEntity):
    """wellbeing Sensor class."""
    def __init__(self, coordinator, config_entry, pnc_id, entity_type, entity_attr, entity_options = None):
        super().__init__(coordinator, config_entry, pnc_id, entity_type, entity_attr)
        if entity_options != None:
            self.options = entity_options

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.get_entity.state

    @property
    def native_unit_of_measurement(self):
        return cast(ApplianceSensor, self.get_entity).unit

    @property
    def state_class(self) -> SensorStateClass | str | None:
        return self.get_entity.state_class
