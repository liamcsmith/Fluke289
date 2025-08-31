from serial import Serial
from datetime import datetime as dtm
from struct import unpack
from typing import Literal, Dict, List, Optional
from gzip import decompress
from time import sleep, gmtime, struct_time
from PIL import Image, ImageFile
from io import BytesIO


class Fluke289:

    # The buttons available to "press" remotely on a Fluke289.
    _buttons = (
        "HOLD", "ONOFF", "MINMAX", "F1", "UP", "LEFT", "RIGHT", "DOWN", "INFO",
        "RANGE", "F3", "BACKLIGHT", "F4", "F2")

    # All the possible map keys within the scope that I can find, not all of
    # these correspond to "set"able properties, some are maps used in the
    # interpretation of output data. These maps are explored via the QEMAP
    # function, all the fields in this tuple will respond to a QEMAP request.
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

    def __init__(self, port: str):

        # Store the device location.
        self._port = port

        # Map out the device properties.
        self._map: Dict[str, Dict[int, str]] = {}
        [self.QEMAP(el) for el in self._map_keys]

        return None

    @property
    def _device(self) -> Serial:

        # Create the device variable.
        tmp = Serial(self._port, baudrate=115200, timeout=0.5)

        # Check that the device is open, if it is return it, if not raise an
        # error as the connection has failed.
        if tmp.isOpen():  # type: ignore
            return tmp
        else:
            msg = "Failed to open device at {}."
            raise Exception(msg.format(self._port))

    @property
    def id(self) -> str:
        return self.query("ID")

    @property
    def model(self) -> str:
        return self.query("ID").split(",")[0]

    @property
    def software_version(self) -> str:
        return self.query("ID").split(",")[1]

    @property
    def serial_number(self) -> int:
        return int(self.query("ID").split(",")[2])

    @property
    def mulitmeter_datetime(self) -> struct_time:
        return gmtime(int(self.query("QMP CLOCK")))

    @property
    def beeper(self) -> str:
        return self.query("QMP BEEPER")

    @beeper.setter
    def beeper(self, val: Literal["OFF", "ON"]) -> None:
        self._map_check(val, "BEEPER")
        self._command("MP BEEPER, {}".format(val))

    @property
    def digits(self) -> int:
        return int(self.query("QMP DIGITS"))

    @digits.setter
    def digits(self, val: Literal[4, 5]) -> None:
        self._map_check("{}".format(val), "DIGITS")
        self._command("MP DIGITS, {}".format(val))

    @property
    def company_name(self) -> str:
        return self.query("QMPQ COMPANY")

    @company_name.setter
    def company_name(self, name: str) -> None:
        self._command("MPQ COMPANY, '{}'".format(name))

    @property
    def operator_name(self) -> str:
        return self.query("QMPQ OPERATOR")

    @operator_name.setter
    def operator_name(self, name: str) -> None:
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
        return self.query("QMP LANG")

    @language.setter
    def language(self,
                 val: Literal["ENGLISH", "CHINESE", "JAPANESE", "ITALIAN",
                              "SPANISH", "GERMAN", "FRENCH"]) -> None:
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
        return int(self.query("QMP LCDCONT"))

    @lcd_contrast.setter
    def lcd_contrast(
            self,
            val: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8,
                         9, 10, 11, 12, 13, 14, 15]) -> None:
        if val not in range(16):
            raise ValueError("Error setting LCD contrast, value should be an"
                             + "integer between 0 and 15 inclusive.")
        self._command("MP LCDCONT, {}".format(val))

    @property
    def continuity_beep_config(self) -> str:
        return self.query("QMP CONTBEEPOS")

    @continuity_beep_config.setter
    def continuity_beep_config(self, val: Literal["SHORT", "OPEN"]) -> None:
        self._map_check(val, "CONTBEEPOS")
        self._command("MP CONTBEEPOS, {}".format(val))

    @property
    def continuity_beep(self) -> str:
        return self.query("QMP CONTBEEP")

    @continuity_beep.setter
    def continuity_beep(self, val: Literal["OFF", "ON"]) -> None:
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
        return int(self.query("QMP ABLTO"))

    @auto_backlight_timeout.setter
    def auto_backlight_timeout(
            self,
            val: Literal[0, 300, 600, 900, 1200, 1500, 1800]) -> None:

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
        return int(self.query("QMP APOFFTO"))

    @auto_poweroff_timeout.setter
    def auto_poweroff_timeout(
            self,
            val: Literal[0, 900, 1500, 2100, 2700, 3600]) -> None:

        # Ensure the value is appropriate before sending to the multimeter.
        if val not in [0, 900, 1500, 2100, 2700, 3600]:
            msg = "Error setting auto_poweroff_timeout, value given was {}, " \
                + "but expected one of [0, 900, 1500, 2100, 2700, 3600]."
            raise ValueError(msg.format(val))

        self._command("MP APOFFTO, {}".format(val))

    @property
    def primary_value(self) -> float:
        return float(self.primary_measurement()["value"])

    # Wrapper method for query that assumes an ascii response.
    def query(self, query: str | bytes) -> str:
        return self._command(query).decode()

    def defaultSetup(self) -> None:
        self._command("DS")

    def resetInstrument(self) -> None:
        self._command("RI")

    def resetMeterProperties(self) -> None:
        self._command("RMP")

    def primary_measurement(self) -> Dict[str, float | str]:
        response = self.query("QM").split(",")
        return {"value": float(response[0]),
                "unit": response[1],
                "state": response[2]}

    def press_button(
            self,
            button: Literal["INFO", "BACKLIGHT", "HOLD", "MINMAX", "RANGE",
                            "UP", "DOWN", "RIGHT", "LEFT", "F1", "F2", "F3",
                            "F4", "ONOFF"]) -> None:

        # Ensure that the button is one of the available options within the
        # multimeter to be pressed.
        if button not in self._buttons:
            raise ValueError("Invalid choice of button.")

        # Send the command to press the button to the multimeter.
        self._command("PRESS {}".format(button))

    def QDDA(self) -> Dict[str,
                           float |
                           List[str] |
                           int |
                           str |
                           "Fluke289RangeData" |
                           Dict[str, "Fluke289Reading"]]:
        """Query the displayed data in an ASCII format."""

        # Get the response in its full form, then split it by comma.
        out = self.query("QDDA").split(",")

        # Seed the dictionary of parsed response data.
        data: Dict[str,
                   float |
                   List[str] |
                   int |
                   str |
                   Fluke289RangeData |
                   Dict[str, Fluke289Reading]] = dict()

        data["primary_function"] = out[0]
        data["secondary_function"] = out[1]
        data["range_data"] = Fluke289RangeData(out[2:6])
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
        data["readings"] = dict()
        for _ in range(data["number_of_readings"]):
            data["readings"][out[0]] = Fluke289Reading(out[1:9])
            # Trim the response so that we pull in the next 9 terms.
            out = out[9:]

        return data

    def QDDB(self) -> None:
        """Query the displayed data in a binary format."""

        raise NotImplementedError("Not yet available.")
        # out = self._command("QDDB")
        # reading_count = self._read_u16(out, 32)
        # reading_count = get_u16(current_bytes, 32)
        # if len(current_bytes) != reading_count * 30 + 34:
        #     raise ValueError(
        #         'By app: qddb parse error, expected %d bytes, got
        #               %d' % ((reading_count * 30 + 34), len(current_bytes)))
        # # tsval = get_double(bytes, 20)
        # # all bytes parsed
        # return {
        #     'primary_function': get_map_value(
        #           'primfunction', current_bytes, 0),
        #     'secondary_function': get_map_value(
        #           'secfunction', current_bytes, 2),
        #     'auto_range': get_map_value('autorange', current_bytes, 4),
        #     'unit': get_map_value('unit', current_bytes, 6),
        #     'range_max': get_double(current_bytes, 8),
        #     'unit_multiplier': get_s16(current_bytes, 16),
        #     'bolt': get_map_value('bolt', current_bytes, 18),
        #     #    'ts' : (tsval < 0.1) ? nil : parse_time(tsval), # 20
        #     'ts': 0,
        #     'mode': get_multimap_value('mode', current_bytes, 28),
        #     'un1': get_u16(current_bytes, 30),
        #     # 32 is reading count
        #     'readings': parse_readings(current_bytes[34:])
        # }
        # return

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
        """(QSMR = Query Saved Measurement(?) Readings)"""
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
        pass

    def QPSI(self) -> None:
        # Saved Peak data?
        pass

    def QMMSI(self) -> None:
        # Saved min/max
        pass

    def QRSI(self,
             recording_number: Optional[int] = None
             ) -> Dict[str, str | int | struct_time | float]:
        """
        This is the data supporting an automated recording of measurements
        made by Fluke 28X the new firmware supports over a dozen 'recordings'
        each of which has its own identifying number that is shown in the
        display when viewing memory on the meter. In QRSI use 0-## with ##
        representing the last recording, not the "identifying number" IOW:
        there are 0 to nn slots holding recordings that might have YMMV
        identifiers. Fluke is clever with this. """

        if (recording_number is None):
            recording_number = 0

        out = self._command("QRSI {:02d}".format(recording_number))

        # I think that this prefix is common across responses, so it is likely
        # a header of sorts.
        out = out.removeprefix(b"#0")

        outdict: Dict[str, str | int | struct_time | float] = {}
        # Read timestamps (8 bytes long at 4->11 and 12->19)
        outdict["sequence_number"] = self._read_u16(out, 0)
        outdict["un2"] = self._read_u16(out, 2)
        outdict["start_time"] = gmtime(self._read_double(out, 4))
        outdict["end_time"] = gmtime(self._read_double(out, 12))
        outdict["sample_interval"] = self._read_double(out, 20)
        outdict["event_threshold"] = self._read_double(out, 28)
        outdict["reading_index"] = self._read_double(out, 36)  # 32 bits?
        outdict["un3"] = self._read_u16(out, 38)
        outdict["number_of_samples"] = self._read_u16(out, 40)
        outdict["un4"] = self._read_u16(out, 42)
        outdict["primary_function"] = self._map[
            "primfunction"][self._read_u16(out, 44)]
        outdict["secondary_function"] = self._map[
            'secfunction'][self._read_u16(out, 46)]
        outdict["auto_range"] = self._map['autorange'][self._read_u16(out, 48)]
        outdict["unit"] = self._map['unit'][self._read_u16(out, 50)]
        outdict["range_max"] = self._read_double(out, 52)
        outdict["unit_multiplier"] = self._read_i16(out, 60)
        outdict["bolt"] = self._map['bolt'][self._read_u16(out, 62)]
        outdict["un8"] = self._read_u16(out, 64)   # ts3?
        outdict["un9"] = self._read_u16(out, 66)   # ts3?
        outdict["un10"] = self._read_u16(out, 68)  # ts3?
        outdict["un11"] = self._read_u16(out, 70)  # ts3?
        outdict["mode"] = self._read_u16(out, 72)  # [TODO] Fix this enum.
        outdict["un12"] = self._read_u16(out, 74)
        return outdict

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
                # forward by ~1020 bytes.
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

    def QEMAP(self, map_name: str) -> None:
        # Get the map for this given name.
        out = self.query("QEMAP {}".format(map_name)).split(",")

        submap_length = int(out.pop(0))

        if len(out) != submap_length * 2:
            raise ValueError("Error parsing QEMAP {}".format(map_name))

        submap = {}
        for i in range(submap_length):
            submap[int(out[2*i])] = out[2*i + 1]

        self._map[map_name] = submap

    def _map_check(self, val: str, submap: str) -> None:

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
                 sleep_time: Optional[float] = None) -> bytes:

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
        with self._device as dev:

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
                raise IOError("Syntax Error")
            case '2':
                raise IOError("Execution error")
            case '5':
                raise IOError("No data available")
            case _:
                raise IOError("Invalid Response")

        # Strip away the carriage returns at the beginning and end of the
        # response.
        response = response.removeprefix(b'\r')
        response = response.removesuffix(b'\r')

        return response

    def _read_u16(self, input_bytes: bytes, offset: int) -> int:

        if offset > 0:
            endian: bytes = input_bytes[offset + 1:offset - 1:-1]
        else:
            endian: bytes = input_bytes[offset + 1::-1]

        return int(unpack('!H', endian)[0])  # type: ignore

    def _read_i16(self, input_bytes: bytes, offset: int) -> int:
        val = self._read_u16(input_bytes, offset)

        if ((val & 0x8000) != 0):
            val = -(0x10000 - val)
        return val

    def _read_double(self, input_bytes: bytes, offset: int) -> float:
        if offset > 0:
            endian_l = input_bytes[offset + 3:offset - 1:-1]
        else:
            endian_l = input_bytes[offset + 3::-1]

        endian_h = input_bytes[offset + 7:offset + 3:-1]
        endian = endian_l + endian_h

        return round(unpack('!d', endian)[0], 8)


class Fluke289RangeData:

    def __init__(self, data: List[str]):
        self.auto_range_state = data[0],
        self.base_unit = data[1]
        self.range_number = int(data[2]),
        self.unit_multiplier = int(data[3])


class Fluke289Reading:

    def __init__(self, data: List[str]):
        self.readingValue = float(data[0])
        self.baseUnit = data[1]
        self.unitMultiplier = int(data[2])
        self.decimalPlaces = int(data[3])
        self.displayDigits = int(data[4])
        self.readingState = data[5]
        self.readingAttribute = data[6]
        self.readingTimeStamp = dtm.fromtimestamp(float(data[7]))


if __name__ == "__main__":
    f = Fluke289("/dev/tty.usbserial-A8008ZYm")
    pass
