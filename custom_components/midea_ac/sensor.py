"""Sensor platform for Midea Smart AC."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (PERCENTAGE, EntityCategory,
                                 UnitOfElectricCurrent,
                                 UnitOfElectricPotential, UnitOfEnergy,
                                 UnitOfFrequency, UnitOfPower,
                                 UnitOfTemperature, UnitOfTime)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from msmart.utils import MideaIntEnum

from .const import (CONF_ENERGY_DATA_FORMAT, CONF_ENERGY_DATA_SCALE,
                    CONF_ENERGY_SENSOR, CONF_POWER_SENSOR, DOMAIN,
                    EnergyFormat)
from .coordinator import (MideaCoordinatorEntity, MideaDeviceUpdateCoordinator,
                          MideaGroup5Entity, MideaGroupEntity)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Setup the sensor platform for Midea Smart AC."""

    _LOGGER.info("Setting up sensor platform.")

    # Fetch coordinator from global data
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device

    entities = [
        # Temperature sensors
        MideaSensor(
            coordinator,
            "indoor_temperature",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            "indoor_temperature",
        ),
        MideaSensor(
            coordinator,
            "outdoor_temperature",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            "outdoor_temperature",
        ),
    ]

    if hasattr(device, "indoor_humidity") and getattr(
        device, "supports_humidity", False
    ):
        entities.append(
            MideaSensor(
                coordinator,
                "indoor_humidity",
                SensorDeviceClass.HUMIDITY,
                PERCENTAGE,
                "indoor_humidity",
            )
        )
    # outdoor_fan_speed is registered below via the group5-gated MideaGroup5Sensor
    # (upstream); TurboLed's unconditional duplicate was dropped to avoid a
    # colliding unique_id.
    entities.append(
        MideaNewSensor(
            coordinator,
            "compressor_frequency",
            SensorDeviceClass.FREQUENCY,
            UnitOfFrequency.HERTZ,
            "Compressor frequency",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )
    entities.append(
        MideaNewSensor(
            coordinator,
            "compressor_current",
            SensorDeviceClass.CURRENT,
            UnitOfElectricCurrent.AMPERE,
            "Compressor current",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )
    entities.append(
        MideaNewSensor(
            coordinator,
            "indoor_target_frequency",
            SensorDeviceClass.FREQUENCY,
            UnitOfFrequency.HERTZ,
            "Indoor target frequency",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )
    entities.append(
        MideaNewSensor(
            coordinator,
            "outdoor_unit_total_current",
            SensorDeviceClass.CURRENT,
            UnitOfElectricCurrent.AMPERE,
            "Outdoor current",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )
    entities.append(
        MideaNewSensor(
            coordinator,
            "outdoor_unit_voltage",
            SensorDeviceClass.VOLTAGE,
            UnitOfElectricPotential.VOLT,
            "Outdoor voltage",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )
    entities.append(
        MideaNewSensor(
            coordinator,
            "T2",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            "Indoor coil temperature (T2)",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )
    entities.append(
        MideaNewSensor(
            coordinator,
            "T3",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            "Outdoor coil temperature (T3)",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )
    entities.append(
        MideaNewSensor(
            coordinator,
            "TP",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            "Discharge temperature (TP)",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )
    entities.append(
        MideaNewSensor(
            coordinator,
            "indoor_fan_speed",
            None,
            "",
            "Indoor fan speed",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )
    entities.append(
        MideaNewSensor(
            coordinator,
            "outdoor_unit_power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
            "Total power",
        )
    )
    entities.append(
        MideaNewSensor(
            coordinator,
            "louver_angle",
            None,
            "",
            "Louver angle",
        )
    )
    # Indoor unit code/version string (read-only). Only present when reported.
    if getattr(device, "in_version", None) is not None:
        entities.append(
            MideaNewSensor(
                coordinator,
                "in_version",
                None,
                None,
                "Firmware version",
                state_class=None,
            )
        )
    # Only add energy sensors if device supports energy requests
    if hasattr(device, "enable_energy_usage_requests"):

        def _get_energy_config(key: str) -> tuple[EnergyFormat, float]:
            config = config_entry.options.get(key)
            format = device.EnergyDataFormat.get_from_name(
                config.get(CONF_ENERGY_DATA_FORMAT).upper()
            )
            scale = config.get(CONF_ENERGY_DATA_SCALE)
            return format, scale

        # Configure energy format
        energy_data_format, energy_scale = _get_energy_config(
            CONF_ENERGY_SENSOR)
        _LOGGER.info(
            "Using energy format %r (scale: %f) for device ID %s.",
            energy_data_format,
            energy_scale,
            coordinator.device.id,
        )

        power_data_format, power_scale = _get_energy_config(CONF_POWER_SENSOR)
        _LOGGER.info(
            "Using power format %r (scale: %f) for device ID %s.",
            power_data_format,
            power_scale,
            coordinator.device.id,
        )

        entities.extend(
            [
                # Energy sensors
                MideaEnergySensor(
                    coordinator,
                    "total_energy_usage",
                    SensorDeviceClass.ENERGY,
                    UnitOfEnergy.KILO_WATT_HOUR,
                    "total_energy_usage",
                    format=energy_data_format,
                    scale=energy_scale,
                    state_class=SensorStateClass.TOTAL,
                ),
                MideaEnergySensor(
                    coordinator,
                    "current_energy_usage",
                    SensorDeviceClass.ENERGY,
                    UnitOfEnergy.KILO_WATT_HOUR,
                    "current_energy_usage",
                    format=energy_data_format,
                    scale=energy_scale,
                    state_class=SensorStateClass.TOTAL_INCREASING,
                ),
                MideaEnergySensor(
                    coordinator,
                    "real_time_power_usage",
                    SensorDeviceClass.POWER,
                    UnitOfPower.WATT,
                    "real_time_power_usage",
                    format=power_data_format,
                    scale=power_scale,
                ),
            ]
        )

    if hasattr(device, "outdoor_fan_speed") and hasattr(
        device, "enable_group5_data_requests"
    ):
        entities.append(
            MideaGroup5Sensor(
                coordinator,
                "outdoor_fan_speed",
                None,
                None,
                "outdoor_fan_speed",
                entity_category=EntityCategory.DIAGNOSTIC,
            )
        )

    # Dev parameter sensors (opt-in, disabled by default). Byte mappings from
    # the T0xAC plugin reference parser, verified on a PortaSplit (00000Q1D).
    if hasattr(device, "enable_group3_data_requests"):
        entities.extend(
            [
                MideaDevParamSensor(
                    coordinator,
                    "expansion_valve_position",
                    None,
                    None,
                    "Expansion valve position",
                    group=3,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "outdoor_target_frequency",
                    SensorDeviceClass.FREQUENCY,
                    UnitOfFrequency.HERTZ,
                    "Outdoor target frequency",
                    group=3,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "ipm_temperature_raw",
                    None,
                    None,
                    "IPM temperature (raw)",
                    group=3,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "dc_bus_voltage_raw",
                    None,
                    None,
                    "DC bus voltage (raw)",
                    group=3,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "outdoor_return_air_temp_raw",
                    None,
                    None,
                    "Return air temperature (raw)",
                    group=3,
                ),
                MideaDevParamFlagsSensor(
                    coordinator,
                    "outdoor_status_flags",
                    None,
                    None,
                    "Outdoor status flags",
                    group=3,
                    active_prop="outdoor_active_flags",
                    status_bits=(
                        "outdoor_ac_fan_low",
                        "outdoor_ac_fan_medium",
                        "outdoor_ac_fan_high",
                        "four_way_valve_on",
                    ),
                ),
            ]
        )

    # Indoor status flags ride on group 2 which is always requested
    if hasattr(device, "indoor_active_faults"):
        entities.extend(
            [
                MideaDevParamFlagsSensor(
                    coordinator,
                    "indoor_fault_flags",
                    None,
                    None,
                    "Indoor fault flags",
                    group=None,
                    active_prop="indoor_active_faults",
                ),
                MideaDevParamFlagsSensor(
                    coordinator,
                    "indoor_limit_flags",
                    None,
                    None,
                    "Indoor frequency limit flags",
                    group=None,
                    active_prop="indoor_active_limits",
                ),
                MideaDevParamFlagsSensor(
                    coordinator,
                    "indoor_load_flags",
                    None,
                    None,
                    "Indoor load flags",
                    group=None,
                    active_prop="indoor_active_loads",
                ),
                MideaDevParamSensor(
                    coordinator,
                    "indoor_target_fan_speed",
                    None,
                    None,
                    "Indoor target fan speed",
                    group=None,
                ),
            ]
        )

    if hasattr(device, "enable_group0_data_requests"):
        entities.extend(
            [
                MideaDevParamSensor(
                    coordinator,
                    "current_run_time",
                    SensorDeviceClass.DURATION,
                    UnitOfTime.SECONDS,
                    "Current run time",
                    group=0,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "total_run_time",
                    SensorDeviceClass.DURATION,
                    UnitOfTime.SECONDS,
                    "Total run time",
                    group=0,
                    state_class=SensorStateClass.TOTAL_INCREASING,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "power_on_time",
                    SensorDeviceClass.DURATION,
                    UnitOfTime.SECONDS,
                    "Power on time",
                    group=0,
                    state_class=SensorStateClass.TOTAL_INCREASING,
                ),
            ]
        )

    if hasattr(device, "compressor_run_time") and hasattr(
        device, "enable_group5_data_requests"
    ):
        entities.extend(
            [
                MideaDevParamSensor(
                    coordinator,
                    "compressor_run_time",
                    SensorDeviceClass.DURATION,
                    UnitOfTime.SECONDS,
                    "Compressor run time",
                    group=5,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "compressor_total_run_time",
                    SensorDeviceClass.DURATION,
                    UnitOfTime.HOURS,
                    "Compressor total run time",
                    group=5,
                    state_class=SensorStateClass.TOTAL_INCREASING,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "max_voltage",
                    SensorDeviceClass.VOLTAGE,
                    UnitOfElectricPotential.VOLT,
                    "Max voltage",
                    group=5,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "min_voltage",
                    SensorDeviceClass.VOLTAGE,
                    UnitOfElectricPotential.VOLT,
                    "Min voltage",
                    group=5,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "compensated_target_temperature",
                    SensorDeviceClass.TEMPERATURE,
                    UnitOfTemperature.CELSIUS,
                    "Compensated target temperature",
                    group=5,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "defrost_step",
                    None,
                    None,
                    "Defrost step",
                    group=5,
                ),
            ]
        )

    if hasattr(device, "enable_group6_data_requests"):
        entities.extend(
            [
                MideaDevParamSensor(
                    coordinator,
                    "fault_count",
                    None,
                    None,
                    "Fault count",
                    group=6,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "max_outdoor_temperature",
                    SensorDeviceClass.TEMPERATURE,
                    UnitOfTemperature.CELSIUS,
                    "Max outdoor temperature",
                    group=6,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "min_outdoor_temperature",
                    SensorDeviceClass.TEMPERATURE,
                    UnitOfTemperature.CELSIUS,
                    "Min outdoor temperature",
                    group=6,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "compressor_peak_current_raw",
                    None,
                    None,
                    "Compressor peak current (raw)",
                    group=6,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "pfc_peak_current_raw",
                    None,
                    None,
                    "PFC peak current (raw)",
                    group=6,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "fan_peak_current_raw",
                    None,
                    None,
                    "Fan peak current (raw)",
                    group=6,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "max_current_raw",
                    None,
                    None,
                    "Max current (raw)",
                    group=6,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "d_axis_current",
                    None,
                    None,
                    "D-axis current (raw)",
                    group=6,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "q_axis_current",
                    None,
                    None,
                    "Q-axis current (raw)",
                    group=6,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "torque_adjust_angle",
                    None,
                    None,
                    "Torque compensation angle (raw)",
                    group=6,
                ),
                MideaDevParamSensor(
                    coordinator,
                    "torque_adjust_value",
                    None,
                    None,
                    "Torque compensation value (raw)",
                    group=6,
                ),
            ]
        )

    add_entities(entities)


class MideaSensor(MideaCoordinatorEntity, SensorEntity):
    """Generic sensor class for Midea AC."""

    def __init__(
        self,
        coordinator: MideaDeviceUpdateCoordinator,
        prop: str,
        device_class: SensorDeviceClass | None,
        unit: str | None,
        translation_key: str | None = None,
        *,
        state_class: SensorStateClass = SensorStateClass.MEASUREMENT,
        entity_category: EntityCategory | None = None,
    ) -> None:
        MideaCoordinatorEntity.__init__(self, coordinator)

        self._prop = prop
        self._device_class = device_class
        self._state_class = state_class
        self._unit = unit
        self._attr_translation_key = translation_key
        self._attr_entity_category = entity_category

    @property
    def device_info(self) -> dict:
        """Return info for device registry."""
        return {
            "identifiers": {(DOMAIN, self._device.id)},
        }

    @property
    def has_entity_name(self) -> bool:
        """Indicates if entity follows naming conventions."""
        return True

    @property
    def unique_id(self) -> str:
        """Return the unique ID of this entity."""
        return f"{self._device.id}-{self._prop}"

    @property
    def available(self) -> bool:
        """Check entity availability."""

        # Sensor is unavailable if device is offline or value is None
        return super().available and self.native_value is not None

    @property
    def device_class(self) -> str:
        """Return the device class of this entity."""
        return self._device_class

    @property
    def state_class(self) -> str:
        """Return the state class of this entity."""
        return self._state_class

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the native units of this entity."""
        return self._unit

    @property
    def native_value(self) -> float | None:
        """Return the current native value."""
        return getattr(self._device, self._prop, None)


class MideaNewSensor(MideaSensor):
    def __init__(self, *args, **kwargs) -> None:
        MideaSensor.__init__(self, *args, **kwargs)

        self._attr_name = self._attr_translation_key
        self._attr_translation_key = None
        self._attr_has_entity_name = False


class MideaEnergySensor(MideaSensor):
    """Energy sensor class for Midea AC."""

    def __init__(
        self, *args, format: MideaIntEnum, scale: float = 1.0, **kwargs
    ) -> None:
        MideaSensor.__init__(self, *args, **kwargs)

        self._format = format
        self._scale = scale
        self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Call super method to ensure lifecycle is properly handled
        await super().async_added_to_hass()

        # Register energy sensor with coordinator
        self.coordinator.register_energy_sensor()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        # Call super method to ensure lifecycle is properly handled
        await super().async_will_remove_from_hass()

        # Unregister energy sensor with coordinator
        self.coordinator.unregister_energy_sensor()

    @property
    def native_value(self) -> float | None:
        """Return the scaled native value."""
        # Manually prepend 'get_' to the property.
        # This is so we don't have to change prop which causes unique ids to change
        get_method = getattr(self._device, f"get_{self._prop}", None)
        if get_method and callable(get_method):
            value = get_method(self._format)
        else:
            value = None

        if value is None:
            return None

        return value * self._scale


class MideaGroup5Sensor(MideaSensor, MideaGroup5Entity):
    """Sensor for Midea AC group 5 data."""

    def __init__(self, *args, **kwargs) -> None:
        MideaSensor.__init__(self, *args, **kwargs)

        # Group5 sensors start disabled in case device doesn't support them
        self._attr_entity_registry_enabled_default = False


class MideaDevParamSensor(MideaSensor, MideaGroupEntity):
    """Diagnostic sensor for Midea AC dev parameter group data."""

    def __init__(self, *args, group: int, **kwargs) -> None:
        MideaSensor.__init__(self, *args, **kwargs)

        self._group = group

        # Dev parameter sensors start disabled since support is device specific
        self._attr_entity_registry_enabled_default = False
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._attr_name = self._attr_translation_key
        self._attr_translation_key = None
        self._attr_has_entity_name = False


class MideaDevParamFlagsSensor(MideaDevParamSensor):
    """Dev parameter sensor exposing decoded status flags.

    The state is the number of active flags, excluding pure status bits
    (e.g. fan stage, four-way valve). Decoded flag names and the raw
    bytes are exposed as attributes.
    """

    def __init__(self, *args, active_prop: str, status_bits=(), **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._active_prop = active_prop
        self._status_bits = set(status_bits)

    @property
    def native_value(self) -> int | None:
        """Return the number of active (non-status) flags."""
        active = getattr(self._device, self._active_prop, None)
        if active is None:
            return None
        return len([flag for flag in active if flag not in self._status_bits])

    @property
    def extra_state_attributes(self) -> dict:
        """Return decoded flag names and raw bytes."""
        active = getattr(self._device, self._active_prop, None)
        raw = getattr(self._device, self._prop, None)
        return {
            "active_flags": active,
            "raw": raw.hex() if raw is not None else None,
        }
