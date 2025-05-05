"""Select platform for Wellbeing."""

import logging
import asyncio

from typing import cast

from homeassistant.components.select import SelectEntity
from homeassistant.const import Platform

from . import WellbeingDataUpdateCoordinator
from .api import ApplianceSelect
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
                    WellbeingSelect(coordinator, entry, pnc_id, entity.entity_type, entity.attr)
                    for entity in appliance.entities
                    if entity.entity_type == Platform.SELECT
                ]
            )


class WellbeingSelect(WellbeingEntity, SelectEntity):
    """wellbeing Select class."""
    def __init__(self, coordinator, config_entry, pnc_id, entity_type, entity_attr):
        super().__init__(coordinator, config_entry, pnc_id, entity_type, entity_attr)
        _LOGGER.debug(f"##current function is:{self.get_entity.state}")
        self._current_option = self.get_entity.state
        self.options = [OperationFunction.COMPLETE, OperationFunction.CONTINUOUS, OperationFunction.DRY, OperationFunction.PURIFY]



    @property
    def current_option(self):
        if self._current_option != self.get_entity.state:
            self._current_option = self.get_entity.state
        return self._current_option
    

    async def async_select_option(self, option: str) -> None:
        _LOGGER.debug(f"##async_select_option")
        if self._current_option == option:
            _LOGGER.debug(f"##async_select_option function: same function, no change, return.")
            return
            
        if option == OperationFunction.CONTINUOUS:
            _LOGGER.debug(f"##async_select_option function: continuous")
            humidifiers = self.hass.data[DOMAIN].get("humidifier_entities", [])
            for humidifier in humidifiers:
                if humidifier.pnc_id == self.pnc_id:
                    await humidifier.async_set_humidity(30, 1)
                    #self.async_write_ha_state()

        elif option == OperationFunction.DRY:
            _LOGGER.debug(f"##async_select_option function: dry")
        elif option == OperationFunction.PURIFY:
            _LOGGER.debug(f"##async_select_option function: purify")
        elif option == OperationFunction.COMPLETE:
            _LOGGER.debug(f"##async_select_option function: complete")
            if self._current_option == OperationFunction.CONTINUOUS:
                _LOGGER.debug(f"##async_select_option function: set to 35")
                humidifiers = self.hass.data[DOMAIN].get("humidifier_entities", [])
                for humidifier in humidifiers:
                    if humidifier.pnc_id == self.pnc_id:
                        await humidifier.async_set_humidity(35, 1)
                        #self.async_write_ha_state()
        else:
            _LOGGER.debug(f"##async_select_option function: unknow funcion, return.")
            return

        self._current_option = option

        await self.api.set_operation_function(self.pnc_id, option)

        self.async_write_ha_state()
        await asyncio.sleep(10)
        await self.coordinator.async_request_refresh()
