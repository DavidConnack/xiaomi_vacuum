"""Xiaomi Vacuum"""
from functools import partial
import logging
import voluptuous as vol

from .miio import DreameVacuum, DeviceException

from homeassistant.components.vacuum import (
    PLATFORM_SCHEMA,
    SUPPORT_STATE,
    SUPPORT_BATTERY,
    SUPPORT_LOCATE,
    SUPPORT_PAUSE,
    SUPPORT_RETURN_HOME,
    SUPPORT_START,
    SUPPORT_STOP,
    SUPPORT_FAN_SPEED,
    STATE_CLEANING,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    STATE_DOCKED,
    STATE_ERROR,
    StateVacuumEntity,
)

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN
from homeassistant.helpers import config_validation as cv, entity_platform

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi Vacuum cleaner"
DATA_KEY = "vacuum.xiaomi_vacuum"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): vol.All(str, vol.Length(min=32, max=32)),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

ATTR_FAN_SPEED = "fan_speed"
ATTR_MAIN_BRUSH_LEFT_TIME = "main_brush_time_left"
ATTR_MAIN_BRUSH_LIFE_LEVEL = "main_brush_life_level"
ATTR_SIDE_BRUSH_LEFT_TIME = "side_brush_time_left"
ATTR_SIDE_BRUSH_LIFE_LEVEL = "side_brush_life_level"
ATTR_FILTER_LIFE_LEVEL = "filter_life_level"
ATTR_FILTER_LEFT_TIME = "filter_left_time"
ATTR_CLEANING_TOTAL_TIME = "total_cleaning_count"

SUPPORT_XIAOMI = (
    SUPPORT_STATE
    | SUPPORT_BATTERY
    | SUPPORT_LOCATE
    | SUPPORT_RETURN_HOME
    | SUPPORT_START
    | SUPPORT_STOP
    | SUPPORT_PAUSE
    | SUPPORT_FAN_SPEED
)

STATE_CODE_TO_STATE = {
    1: STATE_CLEANING,
    2: STATE_IDLE,
    3: STATE_PAUSED,
    4: STATE_ERROR,
    5: STATE_RETURNING,
    6: STATE_DOCKED,
}

SPEED_CODE_TO_NAME = {
    0: "Silent",
    1: "Standard",
    2: "Medium",
    3: "Turbo",
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Xiaomi vacuum cleaner robot platform."""
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    host = config.get(CONF_HOST)
    token = config.get(CONF_TOKEN)
    name = config.get(CONF_NAME)

    # Create handler
    _LOGGER.info("Initializing with host %s (token %s...)", host, token)
    vacuum = DreameVacuum(host, token)

    mirobo = MiroboVacuum(name, vacuum)
    hass.data[DATA_KEY][host] = mirobo

    async_add_entities([mirobo], update_before_add=True)

class MiroboVacuum(StateVacuumEntity):
    """Representation of a Xiaomi Vacuum cleaner robot."""

    def __init__(self, name, vacuum):
        """Initialize the Xiaomi vacuum cleaner robot handler."""
        self._name = name
        self._vacuum = vacuum

        self._fan_speeds = None
        self._fan_speeds_reverse = None

        self.vacuum_state = None
        self.battery_percentage = None
        
        self._current_fan_speed = None

        self._main_brush_time_left = None
        self._main_brush_life_level = None

        self._side_brush_time_left = None
        self._side_brush_life_level = None

        self._filter_life_level = None
        self._filter_left_time = None

        self._total_clean_count = None

        

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the status of the vacuum cleaner."""
        if self.vacuum_state is not None:
            try:
                return STATE_CODE_TO_STATE[int(self.vacuum_state)]
            except KeyError:
                _LOGGER.error(
                    "STATE_CODE not supported: %s",
                    self.vacuum_state,
                )
                return None

    @property
    def battery_level(self):
        """Return the battery level of the vacuum cleaner."""
        if self.vacuum_state is not None:
            return self.battery_percentage

    @property
    def fan_speed(self):
        """Return the fan speed of the vacuum cleaner."""
        if self.vacuum_state is not None:
            speed = self._current_fan_speed
            if speed in self._fan_speeds_reverse:
                return self._fan_speeds_reverse[speed]

            _LOGGER.debug("Unable to find reverse for %s", speed)

            return speed

    @property
    def fan_speed_list(self):
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return list(self._fan_speeds) if self._fan_speeds else []

    @property
    def device_state_attributes(self):
        """Return the specific state attributes of this vacuum cleaner."""
        if self.vacuum_state is not None:
            return {
                ATTR_FAN_SPEED: self._current_fan_speed,
                ATTR_MAIN_BRUSH_LEFT_TIME: self._main_brush_time_left,
                ATTR_MAIN_BRUSH_LIFE_LEVEL: self._main_brush_life_level,
                ATTR_SIDE_BRUSH_LEFT_TIME: self._side_brush_time_left,
                ATTR_SIDE_BRUSH_LIFE_LEVEL: self._side_brush_life_level,
                ATTR_FILTER_LIFE_LEVEL: self._filter_life_level,
                ATTR_FILTER_LEFT_TIME: self._filter_left_time,
                ATTR_CLEANING_TOTAL_TIME: self._total_clean_count,
            } 


    @property
    def supported_features(self):
        """Flag vacuum cleaner robot features that are supported."""
        return SUPPORT_XIAOMI

    async def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a vacuum command handling error messages."""
        try:
            await self.hass.async_add_executor_job(partial(func, *args, **kwargs))
            return True
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            return False

    
    async def async_locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        await self._try_command("Unable to locate the botvac: %s", self._vacuum.find)

    async def async_start(self):
        """Start or resume the cleaning task."""
        await self._try_command(
            "Unable to start the vacuum: %s", self._vacuum.start)

    async def async_stop(self, **kwargs):
        """Stop the vacuum cleaner."""
        await self._try_command("Unable to stop: %s", self._vacuum.stop)

    async def async_pause(self):
        """Pause the cleaning task."""
        await self._try_command("Unable to set start/pause: %s", self._vacuum.stop)

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        await self._try_command("Unable to return home: %s", self._vacuum.return_home)

    async def async_set_fan_speed(self, fan_speed, **kwargs):
        """Set fan speed."""
        if fan_speed in self._fan_speeds:
            fan_speed = self._fan_speeds[fan_speed]
        else:
            try:
                fan_speed = int(fan_speed)
            except ValueError as exc:
                _LOGGER.error(
                    "Fan speed step not recognized (%s). Valid speeds are: %s",
                    exc,
                    self.fan_speed_list,
                )
                return
        await self._try_command(
            "Unable to set fan speed: %s", self._vacuum.set_fan_speed, fan_speed
        )
    

    def update(self):
        """Fetch state from the device."""
        try:
            state = self._vacuum.status()
            self.vacuum_state = state.status

            self._fan_speeds = SPEED_CODE_TO_NAME
            self._fan_speeds_reverse = {v: k for k, v in self._fan_speeds.items()}

            self.battery_percentage = state.battery

            self._total_clean_count = state.total_clean_count

            self._current_fan_speed = state.fan_speed

            self._main_brush_time_left = state.brush_left_time
            self._main_brush_life_level = state.brush_life_level

            self._side_brush_time_left = state.brush_left_time2
            self._side_brush_life_level = state.brush_life_level2

            self._filter_life_level = state.filter_life_level
            self._filter_left_time = state.filter_left_time

            

        except OSError as exc:
            _LOGGER.error("Got OSError while fetching the state: %s", exc)