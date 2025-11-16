#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Fluke289.py

Overview:
This package provides a pythonic interface to the Fluke 289 multimeter, much of
this has been implemented with significant help from a forum thread that exists
online, some parts have been reverse engineered, with other aspects incorrectly
implemented or not yet implemented whatsoever.

No guarantees whatsoever are made to the accuracy of any aspect of this package
but many efforts have been made to verify functionality wherever possible.

Futhermore, this codebase is also not intended to replace any official offering
from Fluke, rather it should be considered as a proof of concept, and a further
demonstration in the value of open source software development.

Examples:

To Be Implemented:
1) QSRR, QSMR, QPSI, QMMSI: Square zero, everything left to do.

Google Python Style Guide:
http://google.github.io/styleguide/pyguide.html

"""

from serial import Serial
from PIL import Image, ImageFile
from struct import unpack
from typing import Literal, Dict, List, Any
from time import sleep, gmtime, struct_time
from io import BytesIO
from gzip import decompress


class Fluke289:

    # Module imports used within the Fluke289 class definition.
    from os.path import isfile
    from json import load as load_json

    # The buttons available to "press" remotely on a Fluke289.
    _buttons = ("ONOFF", "MINMAX", "UP", "LEFT", "RIGHT", "DOWN", "INFO", "F1",
                "F2", "F3", "F4", "RANGE", "BACKLIGHT", "HOLD")

    # All the possible map keys within the scope that I can find, not all of
    # these correspond to "set"able properties, some are maps used in the
    # interpretation of output data. These maps are explored via the QEMAP
    # function, all the fields in this tuple will respond to a QEMAP request.
    _map: Dict[str, Any] = {}
    if isfile("_map.json"):
        with open("_map.json") as f:
            _map = load_json(f)

    _map_keys = (
        "PRIMFUNCTION", "SECFUNCTION", "AUTORANGE", "UNIT", "JACKNAME", "RSOB",
        "RECORDTYPE", "ISSTABLEFLAG", "TRANSIENTSTATE", "LCDMODESTATE", "LANG",
        "STATE", "ATTRIBUTE", "FILEMODE", "BEEPERTESTSTATE", "MEMSIZE", "MODE",
        "READINGID", "SESSIONTYPE", "XAJACKNAME", "TESTPATTERN", "MPDEV_PROPS",
        "JACKPOSITIONSTATUS", "MPQ_PROPS", "BUTTONNAME", "CHANNEL", "MP_PROPS",
        "SAMPLETIME", "PRESSTYPE", "POWERMODE", "LEDSTATE", "CALSTATUS", "RSM",
        "BLIGHTVALS", "ACSMOOTH", "TEMPUNIT", "CONTBEEP", "JACKDETECT", "BOLT",
        "UPDATEMODE", "DBMREF", "PWPOL", "SI", "BLVALS", "CONTBEEPOS", "ABLTO",
        "HZEDGE", "MEMVALS", "DIGITS", "NUMFMT", "DCPOL", "TIMEFMT", "APOFFTO",
        "DATEFMT", "BEEPER", "RECEVENTTH")

    def __init__(self, port: str, remap: bool | None = None):
        """Instantiate an interface with a Fluke 289 multimeter.

        Args:
            port [str]: The location of the USB serial device that provides the
                IR interface with the device.

            remap [bool, Optional]: A flag to signal if the scope parameter
                dictionary should be recalculated, if left blank the dictionary
                will only be mapped if it does not yet exist in the same
                working directory as the Fluke289.py file.

        Returns:
            A Fluke289 object, with methods that allow the exploration and
                utilisation of the interfaces.

        Raises:
            None, though an error may be raised when remapping the parameter
            dictionary.
        """

        if (remap is None):
            remap = False

        # Store the device location.
        self._port = port
        self._device = None

        # Map out the device properties, if the map wasn't predefined then we
        # must remap regardless of user preference.
        if remap or (len(self._map) == 0):

            # If remapping, the write_json mechanism must be imported.
            from json import dump as write_json

            # Blank the class map.
            Fluke289._map: Dict[str, Any] = {}

            # Re populate the map
            [self.QEMAP(el) for el in self._map_keys]

            # Write the new map to file, updating the map for the future.
            with open("_map.json", "w") as f:
                write_json(Fluke289._map, f, indent=4)

        return None

    def __enter__(self) -> Serial:
        """ Context management, called when entering "with" block.

        Args:
            self: The Fluke289 instance.

        Returns:
            A Serial object that handles the interface within the pyserial
            package.

        Raises:
            AssertionError, if the _device property is neither an instance of
                the Serial class, or None.
            Connection error, if the _device property, being an instance of the
                Serial class, does not show as following a call to the open()
                method.
        """

        if (self._device is None):
            # Create the device variable.
            self._device = Serial(self._port, baudrate=115200, timeout=0.5)
        else:
            # Ensure the device is a Serial instance, then open it.
            assert isinstance(self._device, Serial), \
                "Device present, but is of incorrect type?"
            self._device.open()

        # Check that the device is open, if it is return it, if not raise an
        # error as the connection has failed.
        if self._device.is_open:
            return self._device
        else:
            msg = "Failed to open device at {}."
            raise ConnectionError(msg.format(self._port))

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """ Context management, called when exiting "with" block.

        Args:
            self: The Fluke289 instance.

        Returns:
            None.

        Raises:
            RuntimeError, if the _device property is not an instance of the
                Serial class, as is should be set to this when entering the
                "with" block.
            Connection error, if the _device property, being an instance of the
                Serial class, does not show as being closed following a call to
                the close() method.
        """

        if (self._device is None):
            # If the device handle no longer exists, then something has gone
            # seriously wrong.
            raise RuntimeError("Device missing, unable to close.")

        else:
            # The device handle exists as expected, so check if it is open, if
            # so then close it.
            if (self._device.is_open):
                self._device.close()

        if (self._device.is_open):
            raise ConnectionError("Failed to close device.")

        return

    def __del__(self):
        """ Context management, called when deleting the instance.

        Args:
            self: The Fluke289 instance.

        Returns:
            None.

        Raises:
            None.
        """

        # Ensuring that if a Serial instance is held within the instance, that
        # it is closed prior to object deletion.
        if isinstance(self._device, Serial) and self._device.is_open:
            self._device.close()

    @property
    def id(self) -> str:
        """ Device identifier.

        Args:
            self: The Fluke289 instance.

        Returns:
            A string containing the identifier.

        Raises:
            None.
        """
        return self.query("ID")

    @property
    def model(self) -> str:
        """ Device model name.

        Args:
            self: The Fluke289 instance.

        Returns:
            A string containing the name, which should be Fluke 289 or similar.

        Raises:
            None.
        """
        return self.query("ID").split(",")[0]

    @property
    def software_version(self) -> str:
        """ Device software version.

        Args:
            self: The Fluke289 instance.

        Returns:
            A string containing the software version running on the multimeter.

        Raises:
            None.
        """
        return self.query("ID").split(",")[1]

    @property
    def serial_number(self) -> int:
        """ Device serial number.

        Args:
            self: The Fluke289 instance.

        Returns:
            An integer that is equal to the serial number of the multimeter.

        Raises:
            None.
        """
        return int(self.query("ID").split(",")[2])

    @property
    def mulitmeter_datetime(self) -> struct_time:
        """ Device time.

        Args:
            self: The Fluke289 instance.

        Returns:
            The current set time on the multimeter, expressed within a
            struct_time instance.

        Raises:
            None.
        """
        return gmtime(int(self.query("QMP CLOCK")))

    @property
    def beeper(self) -> str:
        """ Device beeper state.

        Args:
            self: The Fluke289 instance.

        Returns:
            A string representing if the beeper within the multimeter is
            enabled.

        Raises:
            None.
        """
        return self.query("QMP BEEPER")

    @beeper.setter
    def beeper(self, val: Literal["OFF", "ON"]) -> None:
        """ Device beeper state setter.

        Args:
            self: The Fluke289 instance.

            val: Either "ON" or "OFF" with this enabling or disabling the
                beeper respectively.

        Returns:
            None.

        Raises:
            None.
        """
        self._map_check(val, "BEEPER")
        self._command("MP BEEPER, {}".format(val))

    @property
    def digits(self) -> int:
        """ Device display number of digits.

        Args:
            self: The Fluke289 instance.

        Returns:
            The number of digits currently used to display values on the
            multimeter, as an integer.

        Raises:
            None.
        """
        return int(self.query("QMP DIGITS"))

    @digits.setter
    def digits(self, val: Literal[4, 5]) -> None:
        """ Device display number of digits setter.

        Args:
            self: The Fluke289 instance.

            val: Either 4 or 5 (given as an integer), to set the multimeter to
                use that many digits when displaying a value.

        Returns:
            None.

        Raises:
            None.
        """
        self._map_check("{}".format(val), "DIGITS")
        self._command("MP DIGITS, {}".format(val))

    @property
    def company_name(self) -> str:
        """ Device Information: Company Name.

        Args:
            self: The Fluke289 instance.

        Returns:
            The company name set on the device information screen, as a string.

        Raises:
            None.
        """
        return self.query("QMPQ COMPANY")

    @company_name.setter
    def company_name(self, name: str) -> None:
        """ Device Information: Company Name settter.

        Args:
            self: The Fluke289 instance.

            name: A string that defines the desired company name, there may be
                a limit to this, I do not know so if it throws an error try
                initially with a shorter alternative.

        Returns:
            None.

        Raises:
            None.
        """
        self._command("MPQ COMPANY, '{}'".format(name))

    @property
    def operator_name(self) -> str:
        """ Device Information: Operator Name.

        Args:
            self: The Fluke289 instance.

        Returns:
            The operator name set on the device information screen, as a
                string.

        Raises:
            None.
        """
        return self.query("QMPQ OPERATOR")

    @operator_name.setter
    def operator_name(self, name: str) -> None:
        """ Device Information: Operator Name setter.

        Args:
            self: The Fluke289 instance.

            name: A string defining the desired Operator Name, there may be a
                limit to this, I do not know so if it throws an error try
                changing your name to something shorter.

        Returns:
            None.

        Raises:
            None.
        """
        self._command("MPQ OPERATOR, '{}'".format(name))

    @property
    def contact_info(self) -> str:
        return self.query("QMPQ CONTACT")

    @contact_info.setter
    def contact_info(self, info: str) -> None:
        self._command("MPQ CONTACT, '{}'".format(info))

    @property
    def site_info(self) -> str:
        return self.query("QMPQ SITE")

    @site_info.setter
    def site_info(self, site: str) -> None:
        self._command("MPQ SITE, '{}'".format(site))

    @property
    def autohold_event_threshold(self):
        return int(self.query("QMP AHEVENTTH"))

    @property
    def recording_event_threshold(self) -> int:
        return int(self.query("QMP RECEVENTTH"))

    @recording_event_threshold.setter
    def recording_event_threshold(
            self,
            val: Literal[0, 1, 4, 5, 10, 15, 20, 25]) -> None:
        self._map_check("{}".format(val), "RECEVENTTH")
        self._command("MP RECEVENTTH, {}".format(val))

    @property
    def language(self) -> str:
        """ Device Information: Language.

        Args:
            self: The Fluke289 instance.

        Returns:
            The language that the multimeter user interface is currently set to
                use, this could be ENGLISH, GERMAN, FRENCH, SPANISH, ITALIAN,
                JAPANESE, or CHINESE.

        Raises:
            None.
        """
        return self.query("QMP LANG")

    @language.setter
    def language(self,
                 val: Literal["ENGLISH", "CHINESE", "JAPANESE", "ITALIAN",
                              "SPANISH", "GERMAN", "FRENCH"]) -> None:
        """ Device Information: Language.

        Args:
            self: The Fluke289 instance.

            val: The language that the user wishes the multimeter to use. This
                could be ENGLISH, GERMAN, FRENCH, SPANISH, ITALIAN, JAPANESE,
                or CHINESE.

        Returns:
            None.

        Raises:
            None.
        """
        self._map_check(val, "LANG")
        self._command("MP LANG, {}".format(val))

    @property
    def RSM(self) -> str:
        return self.query("QMP RSM")

    @RSM.setter
    def RSM(self, val: Literal["ON", "OFF"]) -> None:
        self._map_check(val, "RSM")
        self._command("MP RSM, {}".format(val))

    @property
    def ac_smoothing(self) -> str:
        return self.query("QMP ACSMOOTH")

    @ac_smoothing.setter
    def ac_smoothing(self, val: Literal["OFF", "ON"]) -> None:
        self._map_check(val, "ACSMOOTH")
        self._command("MP ACSMOOTH, {}".format(val))

    @property
    def pw_polarity(self) -> str:
        return self.query("QMP PWPOL")

    @pw_polarity.setter
    def pw_polarity(self, val: Literal["POS", "NEG"]) -> None:
        self._map_check(val, "PWPOL")
        self._command("MP PWPOL, {}".format(val))

    @property
    def temperature_unit(self) -> str:
        return self.query("QMP TEMPUNIT")

    @temperature_unit.setter
    def temperature_unit(self, val: Literal["C", "F"]) -> None:
        self._map_check(val, "TEMPUNIT")
        self._command("MP TEMPUNIT, {}".format(val))

    @property
    def SI(self) -> str:
        return self.query("QMP SI")

    @SI.setter
    def SI(self, val: Literal["OFF", "ON"]) -> None:
        self._map_check(val, "SI")
        self._command("MP SI, {}".format(val))

    @property
    def lcd_contrast(self) -> int:
        """ Device Information: LCD Contrast.

        Args:
            self: The Fluke289 instance.

        Returns:
            The current contrast level of the LCD on the multimeter, this is
            expressed as a non-negative integer with a value up to 15.

        Raises:
            None.
        """
        return int(self.query("QMP LCDCONT"))

    @lcd_contrast.setter
    def lcd_contrast(
            self,
            val: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8,
                         9, 10, 11, 12, 13, 14, 15]) -> None:
        """ Device Information: LCD Contrast setter.

        Args:
            self: The Fluke289 instance.

            val: The desired level of contrast for the multimeter LCD, this
                should be a value expressed as a non-negative integer with a
                value up to 15.

        Returns:
            None.

        Raises:
            None.
        """
        if val not in range(16):
            raise ValueError("Error setting LCD contrast, value should be an"
                             + "integer between 0 and 15 inclusive.")
        self._command("MP LCDCONT, {}".format(val))

    @property
    def continuity_beep_config(self) -> str:
        """ Device Information: Continuity Beep Configuration.

        Args:
            self: The Fluke289 instance.

        Returns:
            The current configuration of the beeper when the multimeter is used
                in the continuity tester mode. This will either be "SHORT" or
                "OPEN", with this values corresponding to a beep when there is
                continuity (a shorted state), or when there is not continuity
                (an open circuit state).

        Raises:
            None.
        """
        return self.query("QMP CONTBEEPOS")

    @continuity_beep_config.setter
    def continuity_beep_config(self, val: Literal["SHORT", "OPEN"]) -> None:
        """ Device Information: Continuity Beep Configuration setter.

        Args:
            self: The Fluke289 instance.

            val: The desired beep configuration for the continuity tester mode,
                this will either be "SHORT" or "OPEN", with the values setting
                a beep when there is continuity (a shorted state), or when
                there is not continuity (an open circuit state).

        Returns:
            None.

        Raises:
            None.
        """
        self._map_check(val, "CONTBEEPOS")
        self._command("MP CONTBEEPOS, {}".format(val))

    @property
    def continuity_beep(self) -> str:
        """ Device Information: Continuity Beep state.

        Args:
            self: The Fluke289 instance.

        Returns:
            Either "ON" or "OFF" as a string with this the state of the beeper
                when used within the continuity tester mode.

        Raises:
            None.
        """
        return self.query("QMP CONTBEEP")

    @continuity_beep.setter
    def continuity_beep(self, val: Literal["OFF", "ON"]) -> None:
        """ Device Information: Continuity Beep setter.

        Args:
            self: The Fluke289 instance.

            val: Either "ON" or "OFF" with this setting the state of the beeper
                when used within the continuity tester mode.

        Returns:
            None.

        Raises:
            None.
        """
        self._map_check(val, "CONTBEEP")
        self._command("MP CONTBEEP, {}".format(val))

    @property
    def date_format(self) -> str:
        return self.query("QMP DATEFMT")

    @date_format.setter
    def date_format(self, val: Literal["MM_DD", "DD_MM"]) -> None:
        self._map_check(val, "DATEFMT")
        self._command("MP DATEFMT, {}".format(val))

    @property
    def time_format(self) -> int:
        return int(self.query("QMP TIMEFMT"))

    @time_format.setter
    def time_format(self, val: Literal[12, 24]) -> None:
        self._map_check("{}".format(val), "TIMEFMT")
        self._command("MP TIMEFMT, {}".format(val))

    @property
    def DC_polarity(self) -> str:
        return self.query("QMP DCPOL")

    @DC_polarity.setter
    def DC_polarity(self, val: Literal["POS", "NEG"]) -> None:
        self._map_check(val, "DCPOL")
        self._command("MP DCPOL, {}".format(val))

    @property
    def temperature_offset(self) -> float:
        return float(self.query("QMP TEMPOS"))

    @temperature_offset.setter
    def temperature_offset_shift(self, val: float) -> None:

        if (val < -100.0) or (val > 100.0):
            msg = "temperature offset should hold a value between -100.0 and" \
                + " 100.0 inclusive."
            raise ValueError(msg)

        self._command("MP TEMPOS, {:.1f}".format(val))

    @property
    def numeric_format(self) -> str:
        return self.query("QMP NUMFMT")

    @numeric_format.setter
    def numeric_format(self, val: Literal["POINT", "COMMA"]) -> None:
        self._map_check(val, "NUMFMT")
        self._command("MP NUMFMT, {}".format(val))

    @property
    def decibel_meter_reference(self) -> int:
        return int(self.query("QMP DBMREF"))

    @decibel_meter_reference.setter
    def decibel_meter_reference(
            self,
            val: Literal[0, 4, 8, 16, 25, 32, 50, 75, 600, 1000]) -> None:
        self._map_check("{}".format(val), "DBMREF")
        self._command("MP DBMREF, {}".format(val))

    @property
    def custom_decibel_meter_reference(self) -> int:
        return int(self.query("QMP CUSDBM"))

    @custom_decibel_meter_reference.setter
    def custom_decibel_meter_reference(self, val: int) -> None:
        if (val not in range(1, 1999)):
            msg = "Error setting custom_decibel_meter_reference, this should" \
                + " be an integer between 1 and 1999 inclusive."
            raise ValueError(msg)
        self._command("MP CUSDBM, {}".format(val))

    @property
    def auto_backlight_timeout(self) -> int:
        """ Device Information: Auto-Backlight Timeout.

        Args:
            self: The Fluke289 instance.

        Returns:
            The number of seconds without a button press that will have to
                elapse before the backlight on the mulitmeter will turn off, a
                value of zero denotes that the backlight will not timeout.

        Raises:
            None.
        """
        return int(self.query("QMP ABLTO"))

    @auto_backlight_timeout.setter
    def auto_backlight_timeout(self,
            val: Literal[0, 300, 600, 900, 1200, 1500, 1800]) -> None:
        """ Device Information: Auto-Backlight Timeout setter.

        Args:
            self: The Fluke289 instance.

            val: The number of seconds without a button press that will have to
                elapse before the backlight on the mulitmeter will turn off, a
                value of zero denotes that the backlight will not timeout.
                Acceptable values include: 0 (Inf), 300 (5 min), 600 (10 min),
                900 (15 min), 1200 (20 min), 1500 (25 min), or 1800 (30 min).

        Returns:
            None.

        Raises:
            None.
        """

        # Ensure that a suitable value is passed in.
        if val not in [0, 300, 600, 900, 1200, 1500, 1800]:
            msg = "Error setting auto backlight timeout, value was {}, " \
                + "expected one of [0, 300, 600, 900, 1200, 1500, 1800]."
            raise ValueError(msg.format(val))

        # If an acceptable value was passed, then send the command to update.
        self._command("MP ABLTO, {}".format(val))

    @property
    def hertz_edge_side(self) -> str:
        return self.query("QMP HZEDGE")

    @hertz_edge_side.setter
    def hertz_edge_side(self,
                        val: Literal["RISING", "FALLING"]) -> None:
        self._map_check(val, "HZEDGE")
        self._command("MP HZEDGE, {}".format(val))

    @property
    def auto_poweroff_timeout(self) -> int:
        """ Device Information: Auto-PowerOff Timeout.

        Args:
            self: The Fluke289 instance.

        Returns:
            The number of seconds without a button press that will have to
                elapse before the mulitmeter will turn off, a value of zero
                denotes that the multimeter will not switch off until either
                the power button is pressed or the batteries run empty.

        Raises:
            None.
        """
        return int(self.query("QMP APOFFTO"))

    @auto_poweroff_timeout.setter
    def auto_poweroff_timeout(
            self,
            val: Literal[0, 900, 1500, 2100, 2700, 3600]) -> None:
        """ Device Information: Auto-PowerOff Timeout setter.

        Args:
            self: The Fluke289 instance.

            val: The number of seconds without a button press that will have to
                elapse before the mulitmeter will turn off, a value of zero
                denotes that the multimeter will not switch off until either
                the power button is pressed or the batteries run empty.
                Acceptable values include: 0, 900, 1500, 2100, 2700, or 3600,
                these correspond to: Inf, 15 min, 25 min, 35 min, 45 min, or 1
                hour respectively.

        Returns:
            None.

        Raises:
            None.
        """

        # Ensure the value is appropriate before sending to the multimeter.
        if val not in [0, 900, 1500, 2100, 2700, 3600]:
            msg = "Error setting auto_poweroff_timeout, value given was {}, " \
                + "but expected one of [0, 900, 1500, 2100, 2700, 3600]."
            raise ValueError(msg.format(val))

        self._command("MP APOFFTO, {}".format(val))

    @property
    def primary_value(self) -> float:
        return float(self.primary_measurement()["value"])

    def query(self, query: str | bytes) -> str:
        """ Wrapper method for passing a query to the mumtimeter, this method
        interprets a successful response from the multimeter as an ascii
        formatted string that must be decoded and returned.

        Args:
            self: The Fluke289 instance.

            query: The command that is to be sent to the multimeter, this is to
                be either a bytestring or a string.

        Returns:
            The response from the multimeter, interpreted as an ascii formatted
                string.

        Raises:
            None.
        """
        return self._command(query).decode()

    def defaultSetup(self) -> None:
        """ Default all settings on the multimeter to their defaults.

        Args:
            self: The Fluke289 instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._command("DS")

    def resetInstrument(self) -> None:
        """ Reset the multimeter.

        Args:
            self: The Fluke289 instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._command("RI")

    def resetMeterProperties(self) -> None:
        """ Reset all the properties within the multimeter.

        Args:
            self: The Fluke289 instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._command("RMP")

    def primary_measurement(self) -> Dict[str, float | str]:
        response = self.query("QM").split(",")
        return {"value": float(response[0]),
                "unit": response[1],
                "state": response[2]}

    def press_button(
            self,
            button: Literal[
                "INFO", "BACKLIGHT", "HOLD", "MINMAX", "RANGE", "UP", "DOWN",
                "RIGHT", "LEFT", "F1", "F2", "F3", "F4", "ONOFF"],
            ) -> None:

        # Ensure that the button is one of the available options within the
        # multimeter to be pressed.
        if button not in self._buttons:
            raise ValueError("Invalid choice of button.")

        # Send the command to press the button to the multimeter.
        self._command("PRESS {}".format(button))

    def QDDA(self) -> Dict[str, str | List[str] | int | "RangeData" | float |
                           List["Reading"]]:
        """Query the displayed data in an ASCII format."""

        # Get the response in its full form, then split it by comma.
        out = self.query("QDDA").split(",")

        # Seed the dictionary of parsed response data.
        data: Dict[str,
                   str |
                   float |
                   int |
                   List[str] |
                   RangeData |
                   List[Reading]] = dict()

        data["primary_function"] = out[0]
        data["secondary_function"] = out[1]
        data["range_data"] = RangeData(out[2:6])
        data["lightning_bolt"] = out[6]
        data["min_max_start_time"] = float(out[7])
        data["number_of_modes"] = int(out[8])

        # Trim the response
        out = out[9:]

        # Work through the modes importing each one.
        data["modes"] = [out[i] for i in range(data["number_of_modes"])]

        # Trim the response
        out = out[data["number_of_modes"]:]

        # Read in the number of readings.
        data["number_of_readings"] = int(out[0])

        # Trim the response
        out = out[1:]

        # Work through the readings, importing each one into a Fluke289Reading
        # instance.
        data["readings"] = \
            [Reading("ascii", out[i*9:(i+1)*9])
             for i in range(data["number_of_readings"])]

        return data

    def QDDB(self) -> Dict[str,
                           str | int | struct_time | float | List["Reading"]]:
        """Query the displayed data in a binary format."""

        out = self._command("QDDB")
        reading_count = _read_u16(out, 32)
        expected_length = reading_count * 30 + 34
        if len(out) != expected_length:
            msg = "QDDB parse error, expected {} bytes, got {}"
            raise ValueError(msg.format(expected_length, len(out)))

        outdict: Dict[str,
                      str | int | struct_time | float | List[Reading]] = {}

        outdict["prim_func"] = self._map["PRIMFUNCTION"][
            str(_read_u16(out, 0))]
        outdict["sece_func"] = self._map["SECFUNCTION"][str(_read_u16(out, 2))]
        outdict["autorange"] = self._map["AUTORANGE"][str(_read_u16(out, 4))]
        outdict["unit"] = self._map["UNIT"][str(_read_u16(out, 6))]
        outdict["range_max"] = _read_double(out, 8)
        outdict["unit_mult"] = _read_i16(out, 16)
        outdict["bolt"] = self._map["BOLT"][str(_read_u16(out, 18))]
        outdict["tsval"] = gmtime(_read_double(out, 20))
        outdict["mode"] = self._map["MODE"][str(_read_u16(out, 28))]
        outdict["un1"] = _read_u16(out, 30)
        outdict["readings"] = [Reading("binary",
                                       out[34+i*30:64+i*30],
                                       self._map)
                               for i in range(reading_count)]
        return outdict

    def QSRR(self) -> None:
        """(QSRR = Query Saved Recorded Readings)

        QSRR is reported to be the function that can access individual
        "samples" in a recording, presumably with the actual recording
        identifier obtained from QRSI. I have not been successful in
        accessing.
        """

        raise NotImplementedError("Not yet available.")
        # ser.write((('QSRR 5, 0').encode('utf-8')))
        # ser.write(149)
        # ser.write(('\r').encode('utf-8'))
        # if ser.read(2): # the OK 0 and CR
        #     data = (ser.read(999))  # .decode('utf-8'))
        #     print(data)
        #     for i in range(0, len(data)):
        #         print(str(i)+','+str((data[i])))
        #         # print (((data[i])))
        # return

    def QSMR(self) -> None:
        """(QSMR = Query Saved Meter/Measurement(?) Readings)"""
        # Saved Measurement
        # res = meter_command('QSMR ' + idx)
        # reading_count = get_u16(res, 36)

        # if len(res) < reading_count * 30 + 38:
        #     raise ValueError(
        #         'By app: qsmr parse error, expected at least %d bytes, got
        #               %d' % (reading_count * 30 + 78, len(res)))

        # return {'[seq_no': get_u16(res, 0),
        #         'un1': get_u16(res, 2)  # 32 bit?
        #         'prim_function': get_map_value('primfunction', res, 4),
        #         'sec_function': get_map_value('secfunction', res, 6),
        #         'auto_range': get_map_value('autorange', res, 8),
        #         'unit': get_map_value('unit', res, 10),
        #         'range_max': get_double(res, 12),
        #         'unit_multiplier': get_s16(res, 20),
        #         'bolt': get_map_value('bolt', res, 22),
        #         'un4': get_u16(res, 24)  # ts?
        #         'un5': get_u16(res, 26),
        #         'un6': get_u16(res, 28),
        #         'un7': get_u16(res, 30),
        #         'mode': get_multimap_value('mode', res, 32),
        #         'un9': get_u16(res, 34),
        #         # 36 is reading count
        #         'readings': parse_readings(res[38:38 + reading_count * 30]),
        #         'name': res[(38 + reading_count * 30):]
        #         }
        raise NotImplementedError("Not yet available.")

    def QPSI(self) -> None:
        """ Query Peak Save(?) Information(?)"""
        raise NotImplementedError("Not yet available.")

    def QMMSI(self) -> None:
        """ Query Min Max Save(?) Information(?)"""
        raise NotImplementedError("Not yet available.")

    def QRSI(self,
             recording_number: int | None = None
             ) -> Dict[str, str | int | struct_time | float]:
        """ Query Recorded Save(?) Information(?)
        This is the data supporting an automated recording of measurements
        made by Fluke 28X the new firmware supports over a dozen 'recordings'
        each of which has its own identifying number that is shown in the
        display when viewing memory on the meter. In QRSI use 0-## with ##
        representing the last recording, not the "identifying number" IOW:
        there are 0 to nn slots holding recordings that might have YMMV
        identifiers. Fluke is clever with this. """

        if (recording_number is None):
            recording_number = 0

        res = self._command("QRSI {:02d}".format(recording_number))

        u16 = _read_u16
        dbl = _read_double
        i16 = _read_i16

        return {
            "sequence_number":    u16(res, 0),
            "un2":                u16(res, 2),
            "start_time":         gmtime(dbl(res, 4)),
            "end_time":           gmtime(dbl(res, 12)),
            "sample_interval":    dbl(res, 20),
            "event_threshold":    dbl(res, 28),
            "reading_index":      dbl(res, 36),  # 32 bits?
            "un3":                u16(res, 38),
            "number_of_samples":  u16(res, 40),
            "un4":                u16(res, 42),
            "primary_function":   self._map["PRIMFUNCTION"][str(u16(res, 44))],
            "secondary_function": self._map['SECFUNCTION'][str(u16(res, 46))],
            "auto_range":         self._map['AUTORANGE'][str(u16(res, 48))],
            "unit":               self._map['UNIT'][str(u16(res, 50))],
            "range_max":          dbl(res, 52),
            "unit_multiplier":    i16(res, 60),
            "bolt":               self._map['BOLT'][str(u16(res, 62))],
            "un8":                u16(res, 64),  # ts3?
            "un9":                u16(res, 66),  # ts3?
            "un10":               u16(res, 68),  # ts3?
            "un11":               u16(res, 70),  # ts3?
            "mode":               self._map["MODE"][str(u16(res, 72))],
            "un12":               u16(res, 74),
            }

    def QSLS(self) -> Dict[str, int]:
        out = self.query("QSLS").split(",")

        return {"nb_recordings":   int(out[0]),
                "nb_min_max":      int(out[1]),
                "nb_peak":         int(out[2]),
                "nb_measurements": int(out[3])}

    def QLCDBM(self) -> ImageFile.ImageFile:
        """ Take a screenshot of the current displayed values on the
        multimeter.

        This method utilises the QLCDBM <offset> command that will give you
        1020 bytes of gzip compressed MS bitmap data at a time. This is called
        repeatedly with increasing values of offset until less than 1020 bytes
        is returned, after which the bitmap buffer can be re-assembled from
        the distinct parts and decompressed.

        Some of the bytes at the start of the response, and the carriage
        return at the end, have to be dropped from the buffer. An offset of
        zero is used initially, which has the side-effect of actually
        capturing and compressing the screenshot, future reads to increasing
        offsets then read this buffer, until a zero offset request is recieved
        at which point a new screenshot is captured and compressed."""

        # Request that the screenshot be captured and compressed, returning
        # the opening 1018 bytes. This command includes a 10 µs delay to
        # ensure that the command has time to complete as it is definitely not
        # instantaneous.
        img: bytes = self._command("QLCDBM 0", 0.01)
        img = img.removeprefix(b"0 #0")

        # The maximum returnable information is 1020 bytes minus the number of
        # bytes within "0 " which is two bytes, so the maximum size of the
        # initial returned buffer is 1018 bytes. This is the max regardless of
        # how big the compressed bitmap is. If the bitmap is larger we have to
        # read in the buffer with non-zero offsets, moving forward in chunks
        # until all the data has been transferred.
        if (len(img) == 1018):

            # Mark that there is more to read, as 1018 bytes is the maximum
            # number of bytes returnable by the initial call.
            more_to_read = True

            # If the initial read did not complete the bitmap, then shift
            # forward by the total number of transferrable bytes in the
            # original response that given an offset of zero is 1018 bytes.
            offset = 1018

            # Looping until the full bitmap has been transferred.
            while more_to_read:

                # Using the non-zero offset, send the command that requests
                # the currently stored screenshot buffer from this new offset
                # forward by a multple of ~1020 bytes.
                tmp: bytes = self._command("QLCDBM {}".format(offset))

                # Remove the opening part of the (already partially cleaned)
                # response, this ensures that only bitmap buffer is left in
                # the tmp variable.
                tmp = tmp.removeprefix("{} #0".format(offset).encode())

                # Measure the number of bytes within this response, this is
                # used to identify if more data remains to be read, and if so
                # to then offset appropraitely to read as much of the data as
                # possible in the next request.
                nbytes = len(tmp)

                # Checking if all the response was used, if so there is more
                # data to be read.
                more_to_read = (nbytes == 1020 - len("{} ".format(offset)))

                # Appending the current response to the image buffer.
                img += tmp

                # Moving the offset forward by the correct number of bytes.
                offset += nbytes

        # Once here, the whole image buffer has been read, and sits within the
        # "img" variable, however it currently is compressed (via GZip) so we
        # call decompress() to extract the entire image in its full form.
        img = decompress(img)

        # Taking the bitmap byte buffer and reading it as an Image, thus
        # translating the screenshot into a sensible format.
        out = Image.open(BytesIO(img))

        return out

    def QSAVNAME(self) -> List[str]:
        """ Query Save Names """

        out: List[str] = []
        for save_num in range(8):
            cmd = 'QSAVNAME {}'.format(save_num)
            out.append(self.query(cmd))

        return out

    def QEMAP(self,
              map_name: str,
              ) -> None:

        # Get the map for this given name.
        out = self.query("QEMAP {}".format(map_name)).split(",")

        submap_length = int(out.pop(0))

        if len(out) != submap_length * 2:
            raise ValueError("Error parsing QEMAP {}".format(map_name))

        submap: Dict[int, str] = {}
        for i in range(submap_length):
            submap[int(out[2*i])] = out[2*i + 1]

        # [TODO] Check why we are seeing integers as quoted strings in the json
        # file. Ideally they should be unquoted so they are not re-imported as
        # strings.

        Fluke289._map[map_name] = submap

    def _map_check(self,
                   val: str,
                   submap: str,
                   ) -> None:
        """ Internal validation method for parameter setting values.

        Args:
            self: The Fluke289 instance.

            val: The item to be checked.

            submap: The desired list of allowable vaules within the multimeter
                map that the item must be a member of, acceptable vaules here
                include those defined in the Fluke289._map_keys class property.

        Returns:
            None.

        Raises:
            ValueError if the item provided within the val argument is not an
                allowed value for the specified setting/submap. If this is
                raised, a list of acceptable values should be given within the
                error that is raised.
        """
        # Look up the relevant scope map within the _map property. Then list
        # all the acceptable states.
        valid_vals = self._map[submap].values()

        # Check if the value passed to the checker is an acceptable one, if it
        # is then return to continue, else raise an error.
        if val in valid_vals:
            return
        else:
            msg = "Error setting multimeter property: {}. The value given " \
                + "was \"{}\", acceptable values include: "
            msg = msg.format(submap, val)

            # Listing out and formating acceptable values for the property in
            # question.
            vv_1 = ["\"{}\", ".format(el) for el in valid_vals]
            vv_2 = ["and \"{}\".".format(el) for el in valid_vals]
            vv_1 = "".join(vv_1[:-1])

            raise ValueError(msg + vv_1 + vv_2[-1])

    def _command(self,
                 name: str | bytes,
                 sleep_time: float | None = None,
                 ) -> bytes:

        if sleep_time is not None:
            sleep_time = float(sleep_time)

        # Ensure the command is a string (or a bytes encoded string).
        if not (isinstance(name, bytes) or isinstance(name, str)):
            raise ValueError("Command should passed as a string!")

        # If name is a byte stream already, then ensure it ends with the b"\r"
        # block for termination.
        if isinstance(name, bytes):
            if not name.endswith(b"\r"):
                name += b"\r"

        # If name is a string, as we would want normally, ensure it ends with
        # the string "\r", and then encode it to a bytes stream.
        if isinstance(name, str):
            if not name.endswith("\r"):
                name += "\r"

            # Encode it to bytes.
            name = name.encode()

        # Open the device, send the command, and then read the response.
        with self as dev:

            # Sending the command.
            dev.write(name)

            if sleep_time is not None:
                sleep(sleep_time)

            # Read in the response.
            response = dev.readall()

        # The first character of the response is a flag describing the
        # successfulness of the command, zero is all good, if it is zero then
        # we strip that part away and continue.
        match response[0:1].decode():
            case '0':
                response = response[1:]
            case '1':
                raise IOError("Syntax Error.")
            case '2':
                raise IOError("Execution error.")
            case '5':
                raise IOError("No data available.")
            case _:
                raise IOError("Invalid Response.")

        # Strip the carriage returns at the beginning and end of the response,
        # and the #0 that seems to be tagged (maybe as part of a frame) to
        # binary responses.
        response = response.removeprefix(b'\r')
        response = response.removesuffix(b'\r')
        response = response.removeprefix(b"#0")

        return response


class RangeData:

    def __init__(self, data: List[str]):

        assert (len(data) == 4), "data is an incorrect length."

        self.auto_range = data[0],
        self.base_unit = data[1]
        self.range_number = int(data[2]),
        self.unit_multiplier = int(data[3])

        return


class Reading:

    def __init__(self,
                 mode: Literal["binary", "ascii"],
                 data: List[str] | bytes,
                 map: Dict[str, Any] | None = None):

        # Ascii or Binary formatted instantiation cases, handling this by the
        # "mode" argument which is specified by the caller, this choice is
        # mainly made so that assertions on argument type can be used to ensure
        # validity, rather than using the types to infer the parsing desired.
        # This is a reflection of the type fluidity that python allows.
        match mode:
            case "ascii":

                msg = "ascii reading data should be list of strings."
                assert isinstance(data, list), msg
                assert all([isinstance(el, str) for el in data]), msg
                assert (len(data) == 8), "data is an incorrect length."

                self.id = data[0]
                self.value = float(data[1])
                self.unit = data[2]
                self.unit_multiplier = int(data[3])
                self.decimal_places = int(data[4])
                self.displayed_digits = int(data[5])
                self.reading_state = data[6]
                self.reading_attribute = data[7]
                self.time_stamp = gmtime(float(data[8]))

            case "binary":

                assert isinstance(data, bytes)
                assert (len(data) == 30), "data is an incorrect length."
                assert (map is not None), "no map to parse binary reading."

                u16 = _read_u16
                i16 = _read_i16
                dbl = _read_double

                self.reading_id = map["READINGID"][str(u16(data, 0))]
                self.value = dbl(data, 2)
                self.unit = map["UNIT"][str(u16(data, 10))]
                self.unit_multiplier = i16(data, 12)
                self.decimal_places = u16(data, 14)
                self.display_digits = u16(data, 16)
                self.reading_state = map["STATE"][str(u16(data, 18))]
                self.reading_attribute = map["ATTRIBUTE"][str(u16(data, 20))]
                self.time_stamp = gmtime(dbl(data, 22))

        return


def _read_double(input_bytes: bytes, offset: int) -> float:

    if offset > 0:
        endian_l = input_bytes[offset + 3:offset - 1:-1]
    else:
        endian_l = input_bytes[offset + 3::-1]

    endian_h = input_bytes[offset + 7:offset + 3:-1]
    endian = endian_l + endian_h

    return round(unpack('!d', endian)[0], 8)


def _read_u16(input_bytes: bytes, offset: int) -> int:

    if offset > 0:
        endian: bytes = input_bytes[offset + 1:offset - 1:-1]
    else:
        endian: bytes = input_bytes[offset + 1::-1]

    return int(unpack('!H', endian)[0])  # type: ignore


def _read_i16(input_bytes: bytes, offset: int) -> int:
    val = _read_u16(input_bytes, offset)

    if ((val & 0x8000) != 0):
        val = -(0x10000 - val)
    return val


if __name__ == "__main__":
    f = Fluke289("/dev/tty.usbserial-A8008ZYm")
    pass
