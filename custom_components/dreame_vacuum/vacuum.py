from __future__ import annotations

import voluptuous as vol
from typing import Final

from .coordinator import DreameVacuumDataUpdateCoordinator
from .entity import DreameVacuumEntity

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.components.vacuum import (
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    VacuumEntity,
    VacuumEntityFeature,
)

from .dreame import DreameVacuumState, InvalidActionException
from .const import (
    DOMAIN,
    INPUT_CLEANING_ORDER,
    INPUT_DND_ENABLED,
    INPUT_DND_END,
    INPUT_DND_START,
    INPUT_FAN_SPEED,
    INPUT_LANGUAGE_ID,
    INPUT_LINE,
    INPUT_MAP_ID,
    INPUT_MAP_NAME,
    INPUT_MAP_URL,
    INPUT_MD5,
    INPUT_MOP_ARRAY,
    INPUT_REPEATS,
    INPUT_ROTATION,
    INPUT_SEGMENT,
    INPUT_SEGMENT_ID,
    INPUT_SEGMENT_NAME,
    INPUT_SEGMENTS_ARRAY,
    INPUT_SIZE,
    INPUT_URL,
    INPUT_VELOCITY,
    INPUT_WALL_ARRAY,
    INPUT_WATER_LEVEL,
    INPUT_ZONE,
    INPUT_ZONE_ARRAY,
    SERVICE_CLEAN_ZONE,
    SERVICE_CLEAN_SEGMENT,
    SERVICE_CLEAR_WARNING,
    SERVICE_INSTALL_VOICE_PACK,
    SERVICE_MERGE_SEGMENTS,
    SERVICE_MOVE_REMOTE_CONTROL_STEP,
    SERVICE_RENAME_MAP,
    SERVICE_RENAME_SEGMENT,
    SERVICE_REQUEST_MAP,
    SERVICE_SELECT_MAP,
    SERVICE_DELETE_MAP,
    SERVICE_RESTORE_MAP,
    SERVICE_SET_CLEANING_ORDER,
    SERVICE_SET_CUSTOM_CLEANING,
    SERVICE_SET_DND,
    SERVICE_SET_RESTRICTED_ZONE,
    SERVICE_SET_WATER_LEVEL,
    SERVICE_SPLIT_SEGMENTS,
    SERVICE_SAVE_TEMPORARY_MAP,
    SERVICE_DISCARD_TEMPORARY_MAP,
    SERVICE_REPLACE_TEMPORARY_MAP,
)

SUPPORT_DREAME = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.SEND_COMMAND
    | VacuumEntityFeature.LOCATE
    | VacuumEntityFeature.STATE
    | VacuumEntityFeature.STATUS
    | VacuumEntityFeature.BATTERY
    | VacuumEntityFeature.MAP
)


STATE_CODE_TO_STATE: Final = {
    DreameVacuumState.UNKNOWN: STATE_UNKNOWN,
    DreameVacuumState.SWEEPING: STATE_CLEANING,
    DreameVacuumState.IDLE: STATE_IDLE,
    DreameVacuumState.PAUSED: STATE_PAUSED,
    DreameVacuumState.ERROR: STATE_ERROR,
    DreameVacuumState.RETURNING: STATE_RETURNING,
    DreameVacuumState.CHARGING: STATE_DOCKED,
    DreameVacuumState.MOPPING: STATE_CLEANING,
    DreameVacuumState.DRYING: STATE_DOCKED,
    DreameVacuumState.WASHING: STATE_DOCKED,
    DreameVacuumState.RETURNING_WASHING: STATE_RETURNING,
    DreameVacuumState.BUILDING: STATE_DOCKED,
    DreameVacuumState.SWEEPING_AND_MOPPING: STATE_CLEANING,
    DreameVacuumState.CHARGING_COMPLETED: STATE_DOCKED,
    DreameVacuumState.UPGRADING: STATE_IDLE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Dreame Vacuum based on a config entry."""
    coordinator: DreameVacuumDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_REQUEST_MAP,
        {},
        DreameVacuum.async_request_map.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_CLEAR_WARNING,
        {},
        DreameVacuum.async_clear_warning.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_SELECT_MAP,
        {
            vol.Required(INPUT_MAP_ID): cv.positive_int,
        },
        DreameVacuum.async_select_map.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_DELETE_MAP,
        {
            vol.Optional(INPUT_MAP_ID): cv.positive_int,
        },
        DreameVacuum.async_delete_map.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_SAVE_TEMPORARY_MAP,
        {},
        DreameVacuum.async_save_temporary_map.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_DISCARD_TEMPORARY_MAP,
        {},
        DreameVacuum.async_discard_temporary_map.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_REPLACE_TEMPORARY_MAP,
        {
            vol.Optional(INPUT_MAP_ID): cv.positive_int,
        },
        DreameVacuum.async_replace_temporary_map.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_CLEAN_ZONE,
        {
            vol.Required(INPUT_ZONE): vol.All(
                list,
                [
                    vol.ExactSequence(
                        [
                            vol.Coerce(int),
                            vol.Coerce(int),
                            vol.Coerce(int),
                            vol.Coerce(int),
                        ]
                    )
                ],
            ),
            vol.Optional(INPUT_REPEATS): vol.All(
                vol.Coerce(int), vol.Clamp(min=1, max=3)
            ),
        },
        DreameVacuum.async_clean_zone.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_CLEAN_SEGMENT,
        {
            vol.Required(INPUT_SEGMENTS_ARRAY): vol.Any(
                vol.Coerce(int), [vol.Coerce(int)]
            ),
            vol.Optional(INPUT_REPEATS): vol.All(
                vol.Coerce(int), vol.Clamp(min=1, max=3)
            ),
            vol.Optional(INPUT_FAN_SPEED): vol.All(
                vol.Coerce(int), vol.Clamp(min=0, max=3)
            ),
            vol.Optional(INPUT_WATER_LEVEL): vol.All(
                vol.Coerce(int), vol.Clamp(min=1, max=3)
            ),
        },
        DreameVacuum.async_clean_segment.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_SET_RESTRICTED_ZONE,
        {
            vol.Optional(INPUT_WALL_ARRAY): vol.All(
                list,
                [
                    vol.ExactSequence(
                        [
                            vol.Coerce(int),
                            vol.Coerce(int),
                            vol.Coerce(int),
                            vol.Coerce(int),
                        ]
                    )
                ],
            ),
            vol.Optional(INPUT_ZONE_ARRAY): vol.All(
                list,
                [
                    vol.ExactSequence(
                        [
                            vol.Coerce(int),
                            vol.Coerce(int),
                            vol.Coerce(int),
                            vol.Coerce(int),
                        ]
                    )
                ],
            ),
            vol.Optional(INPUT_MOP_ARRAY): vol.All(
                list,
                [
                    vol.ExactSequence(
                        [
                            vol.Coerce(int),
                            vol.Coerce(int),
                            vol.Coerce(int),
                            vol.Coerce(int),
                        ]
                    )
                ],
            ),
        },
        DreameVacuum.async_set_restricted_zone.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_MOVE_REMOTE_CONTROL_STEP,
        {
            vol.Required(INPUT_VELOCITY): vol.All(
                vol.Coerce(int), vol.Clamp(min=-300, max=100)
            ),
            vol.Required(INPUT_ROTATION): vol.All(
                vol.Coerce(int), vol.Clamp(min=-128, max=128)
            ),
        },
        DreameVacuum.async_remote_control_move_step.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_INSTALL_VOICE_PACK,
        {
            vol.Required(INPUT_LANGUAGE_ID): cv.string,
            vol.Required(INPUT_URL): cv.string,
            vol.Required(INPUT_MD5): cv.string,
            vol.Required(INPUT_SIZE): cv.positive_int,
        },
        DreameVacuum.async_install_voice_pack.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_RENAME_MAP,
        {
            vol.Required(INPUT_MAP_ID): cv.positive_int,
            vol.Required(INPUT_MAP_NAME): cv.string,
        },
        DreameVacuum.async_rename_map.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_RESTORE_MAP,
        {
            vol.Required(INPUT_MAP_ID): cv.positive_int,
            vol.Required(INPUT_MAP_URL): cv.string,
        },
        DreameVacuum.async_restore_map.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_MERGE_SEGMENTS,
        {
            vol.Required(INPUT_MAP_ID): cv.positive_int,
            vol.Required(INPUT_SEGMENTS_ARRAY): vol.All(
                [vol.Coerce(int)]
            ),
        },
        DreameVacuum.async_merge_segments.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_SPLIT_SEGMENTS,
        {
            vol.Required(INPUT_MAP_ID): cv.positive_int,
            vol.Required(INPUT_SEGMENT): vol.All(vol.Coerce(int)),
            vol.Required(INPUT_LINE): vol.All(
                list,
                vol.ExactSequence(
                    [
                        vol.Coerce(int),
                        vol.Coerce(int),
                        vol.Coerce(int),
                        vol.Coerce(int),
                    ]
                ),
            ),
        },
        DreameVacuum.async_split_segments.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_RENAME_SEGMENT,
        {
            vol.Required(INPUT_SEGMENT_ID): cv.positive_int,
            vol.Required(INPUT_SEGMENT_NAME): cv.string,
        },
        DreameVacuum.async_rename_segment.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_SET_CLEANING_ORDER,
        {
            vol.Required(INPUT_CLEANING_ORDER): cv.ensure_list,
        },
        DreameVacuum.async_set_cleaning_order.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_SET_CUSTOM_CLEANING,
        {
            vol.Required(INPUT_FAN_SPEED): cv.ensure_list,
            vol.Required(INPUT_WATER_LEVEL): cv.ensure_list,
            vol.Required(INPUT_REPEATS): cv.ensure_list,
        },
        DreameVacuum.async_set_custom_cleaning.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_SET_WATER_LEVEL,
        {
            vol.Required(INPUT_WATER_LEVEL): cv.string,
        },
        DreameVacuum.async_set_water_level.__name__,
    )

    platform.async_register_entity_service(
        SERVICE_SET_DND,
        {
            vol.Required(INPUT_DND_ENABLED): cv.boolean,
            vol.Optional(INPUT_DND_START): cv.string,
            vol.Optional(INPUT_DND_END): cv.string,
        },
        DreameVacuum.async_set_dnd.__name__,
    )

    async_add_entities([DreameVacuum(coordinator)])


class DreameVacuum(DreameVacuumEntity, VacuumEntity):
    """Representation of a Dreame Vacuum cleaner robot."""

    def __init__(self, coordinator: DreameVacuumDataUpdateCoordinator) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)

        self._attr_supported_features = SUPPORT_DREAME
        self._attr_device_class = DOMAIN
        self._attr_name = coordinator.data.name
        self._attr_unique_id = f"{coordinator.data.mac}_" + DOMAIN
        self._set_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._set_attrs()
        self.async_write_ha_state()

    def _set_attrs(self):
        if self.device.status.has_error:
            self._attr_icon = "mdi:alert-circle"  # mdi:robot-vacuum-alert
        elif self.device.status.has_warning:
            self._attr_icon = "mdi:alert"  # mdi:robot-vacuum-alert
        elif self.device.status.sleeping:
            self._attr_icon = "mdi:sleep"
        elif self.device.status.charging:
            self._attr_icon = "mdi:ev-station"
        elif self.device.status.paused:
            self._attr_icon = "mdi:pause-circle"
        else:
            self._attr_icon = "mdi:robot-vacuum"

        if self.device.status.started and (self.device.status.customized_cleaning and not self.device.status.zone_cleaning):
            self._attr_fan_speed_list = [STATE_UNAVAILABLE.capitalize()]
            self._attr_fan_speed = STATE_UNAVAILABLE.capitalize()
        else:
            self._attr_fan_speed_list = list({k.capitalize() for k in self.device.status.fan_speed_list})
            self._attr_fan_speed_list.reverse()
            self._attr_fan_speed = self.device.status.fan_speed_name.capitalize()

        self._attr_battery_level = self.device.status.battery_level           
        self._attr_extra_state_attributes = self.device.status.attributes
        self._attr_state = STATE_CODE_TO_STATE.get(self.device.status.state, STATE_UNKNOWN)
        self._attr_status = self.device.status.status_name.replace("_", " ").capitalize()
        
    @property
    def state(self) -> str | None:
        """Return the state of the vacuum cleaner."""
        return self._attr_state

    @property
    def status(self) -> str | None:
        """Return the status of the vacuum cleaner."""
        return self._attr_status

    @property
    def supported_features(self) -> int:
        """Flag vacuum cleaner features that are supported."""
        return self._attr_supported_features
    
    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the extra state attributes of the entity."""
        return self._attr_extra_state_attributes

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._attr_available and self.device.device_connected

    async def async_locate(self, **kwargs) -> None:
        """Locate the vacuum cleaner."""
        await self._try_command("Unable to call locate: %s", self.device.locate)

    async def async_start(self) -> None:
        """Start or resume the cleaning task."""
        await self._try_command("Unable to call start: %s", self.device.start)

    async def async_start_pause(self) -> None:
        """Start or resume the cleaning task."""
        await self._try_command(
            "Unable to call start_pause: %s", self.device.start_pause
        )

    async def async_stop(self, **kwargs) -> None:
        """Stop the vacuum cleaner."""
        await self._try_command("Unable to call stop: %s", self.device.stop)

    async def async_pause(self) -> None:
        """Pause the cleaning task."""
        await self._try_command("Unable to call pause: %s", self.device.pause)

    async def async_return_to_base(self, **kwargs) -> None:
        """Set the vacuum cleaner to return to the dock."""
        await self._try_command(
            "Unable to call return_to_base: %s", self.device.return_to_base
        )

    async def async_clean_zone(self, zone, repeats=1) -> None:
        await self._try_command(
            "Unable to call clean_zone: %s", self.device.clean_zone, zone, repeats
        )

    async def async_clean_segment(
        self, segments, repeats=1, fan_speed="", water_level=""
    ) -> None:
        """Clean selected segments."""
        await self._try_command(
            "Unable to call clean_segment: %s",
            self.device.clean_segment,
            segments,
            repeats,
            fan_speed,
            water_level,
        )

    async def async_set_restricted_zone(self, walls="", zones="", no_mops="") -> None:
        """Create restricted zone."""
        await self._try_command(
            "Unable to call set_restricted_zone: %s",
            self.device.set_restricted_zone,
            walls,
            zones,
            no_mops,
        )

    async def async_remote_control_move_step(
        self, rotation: int = 0, velocity: int = 0, duration: int = 1500
    ) -> None:
        """Remote control the robot."""
        await self._try_command(
            "Unable to call remote_control_move_step: %s",
            self.device.remote_control_move_step,
            rotation,
            velocity,
            duration,
        )

    async def async_set_fan_speed(self, fan_speed, **kwargs) -> None:
        """Set fan speed."""
        if self.device.status.started and (self.device.status.customized_cleaning and not self.device.status.zone_cleaning):
            raise InvalidActionException(
                "Cannot set fan speed when customized cleaning is enabled"
            )

        if isinstance(fan_speed, str):
            fan_speed = fan_speed.lower().replace(" ", "_")
        if fan_speed in self.device.status.fan_speed_list:
            fan_speed = self.device.status.fan_speed_list[fan_speed]
        else:
            try:
                fan_speed = int(fan_speed)
            except ValueError as exc:
                raise HomeAssistantError(
                    "Fan speed not recognized (%s). Valid options: %s",
                    exc,
                    self.fan_speed_list,
                ) from None
        await self._try_command(
            "Unable to set fan speed: %s", self.device.set_fan_speed, fan_speed
        )

    async def async_set_water_level(self, water_level, **kwargs) -> None:
        """Set water level."""
        if isinstance(water_level, str):
            water_level = water_level.lower().replace(" ", "_")
        if water_level in self.device.status.water_level_list:
            water_level = self.device.status.water_level_list[water_level]
        else:
            try:
                water_level = int(water_level)
            except ValueError as exc:
                raise HomeAssistantError(
                    "Water level not recognized (%s). Valid options: %s",
                    exc,
                    self._water_level_list,
                ) from None
        await self._try_command(
            "Unable to set water level: %s", self.device.set_water_level, water_level
        )

    async def async_select_map(self, map_id) -> None:
        """Switch selected map."""
        await self._try_command(
            "Unable to switch to selected map: %s", self.device.select_map, map_id
        )

    async def async_delete_map(self, map_id=None) -> None:
        """Delete a map."""
        await self._try_command(
            "Unable to delete map: %s", self.device.delete_map, map_id
        )

    async def async_save_temporary_map(self) -> None:
        """Save the temporary map."""
        await self._try_command(
            "Unable to save map: %s", self.device.save_temporary_map
        )

    async def async_discard_temporary_map(self) -> None:
        """Discard the temporary map."""
        await self._try_command(
            "Unable to discard temporary map: %s", self.device.discard_temporary_map
        )

    async def async_replace_temporary_map(self, map_id=None) -> None:
        """Replace the temporary map with another saved map."""
        await self._try_command(
            "Unable to replace temporary map: %s",
            self.device.replace_temporary_map,
            map_id,
        )

    async def async_request_map(self) -> None:
        """Request new map."""
        await self._try_command(
            "Unable to call request_map: %s", self.device.request_map
        )

    async def async_clear_warning(self) -> None:
        """Dismiss error code."""
        await self._try_command(
            "Unable to call clear_warning: %s", self.device.clear_warning
        )

    async def async_rename_map(self, map_id, map_name="") -> None:
        """Rename a map"""
        if map_name != "":
            await self._try_command(
                "Unable to call rename_map: %s",
                self.device.rename_map,
                map_id,
                map_name,
            )

    async def async_restore_map(self, map_id, map_url) -> None:
        """Restore a map"""
        if map_url and map_url != "":
            await self._try_command(
                "Unable to call restore_map: %s",
                self.device.restore_map,
                map_id,
                map_url,
            )

    async def async_rename_segment(self, segment_id, segment_name="") -> None:
        """Rename a segment"""
        if segment_name != "":
            await self._try_command(
                "Unable to call set_segment_name: %s",
                self.device.set_segment_name,
                segment_id,
                0,
                segment_name,
            )

    async def async_merge_segments(self, map_id, segments=None) -> None:
        """Merge segments"""
        if segments is not None:
            await self._try_command(
                "Unable to call merge_segments: %s",
                self.device.merge_segments,
                map_id,
                segments,
            )

    async def async_split_segments(self, map_id, segment, line) -> None:
        """Split segments"""
        if segment is not None and line is not None:
            await self._try_command(
                "Unable to call split_segments: %s",
                self.device.split_segments,
                map_id,
                segment,
                line,
            )

    async def async_set_cleaning_order(self, cleaning_order) -> None:
        """Set cleaning order"""
        if cleaning_order != "" and cleaning_order is not None:
            await self._try_command(
                "Unable to call cleaning_order: %s",
                self.device.set_cleaning_order,
                cleaning_order,
            )

    async def async_set_custom_cleaning(self, fan_speed, water_level, repeats) -> None:
        """Set custom cleaning"""
        if (
            fan_speed != ""
            and fan_speed is not None
            and water_level != ""
            and water_level is not None
            and repeats != ""
            and repeats is not None
        ):
            await self._try_command(
                "Unable to call set_custom_cleaning: %s",
                self.device.set_custom_cleaning,
                fan_speed,
                water_level,
                repeats,
            )

    async def async_install_voice_pack(self, lang_id, url, md5, size, **kwargs) -> None:
        """install a custom language pack"""
        await self._try_command(
            "Unable to call install_voice_pack: %s",
            self.device.install_voice_pack,
            lang_id,
            url,
            md5,
            size,
        )

    async def async_send_command(self, command: str, params, **kwargs) -> None:
        """Send a command to a vacuum cleaner."""
        await self._try_command(
            "Unable to call send_command: %s", self.device.send_command, command, params
        )

    async def async_set_dnd(self, dnd_enabled, dnd_start="", dnd_end="") -> None:
        """Set do not disturb function"""

        await self._try_command(
            "Unable to call set_dnd_enabled: %s",
            self.device.set_dnd_enabled,
            dnd_enabled,
        )
        if dnd_start != "" and dnd_start is not None:
            await self._try_command(
                "Unable to call set_dnd_start: %s", self.device.set_dnd_start, dnd_start
            )
        if dnd_end != "" and dnd_end is not None:
            await self._try_command(
                "Unable to call set_dnd_end: %s", self.device.set_dnd_end, dnd_end
            )