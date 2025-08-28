import serial
from datetime import datetime as dtm
from struct import unpack
from typing import Literal, Dict, List, Optional
from gzip import decompress
from time import sleep
from PIL import Image, ImageFile
from io import BytesIO


class Fluke289:

    # The buttons available to "press" remotely on a Fluke289.
    _buttons = ("HOLD", "ONOFF", "MINMAX", "F1", "UP", "RANGE",
                "F2", "DOWN", "INFO", "F3", "LEFT", "BACKLIGHT",
                "F4", "RIGHT")

    def __init__(self, port: str):
        self._port = port
        return None

    @property
    def _device(self) -> serial.Serial:

        # Create the device variable.
        tmp = serial.Serial(self._port, baudrate=115200, timeout=0.1)

        # Check that the device is open, if it is return it, if not raise an
        # error as the connection has failed.
        if tmp.isOpen():  # type: ignore
            return tmp
        else:
            msg = "Failed to open device at {}."
            raise Exception(msg.format(self._port))

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
                name = name + b"\r"

        # If name is a string, as we would want normally, ensure it ends with
        # the string "\r", and then encode it to a bytes stream.
        if isinstance(name, str):
            if not name.endswith("\r"):
                name = name + "\r"

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

    # Wrapper method for query that assumes an ascii response.
    def query(self, query: str | bytes) -> str:
        return self._command(query).decode()

    @property
    def id(self) -> str:
        return self.query("ID")

    @property
    def beeper(self) -> str:
        return self.query("QMP BEEPER")

    @beeper.setter
    def beeper(self, val: Literal["ON", "OFF"]):
        return self.query("MP BEEPER, " + val)

    @property
    def digits(self) -> str:
        return self.query("QMP DIGITS")

    @property
    def company_name(self) -> str:
        return self.query("QMPQ COMPANY")

    @company_name.setter
    def company_name(self, name: str):
        self._command("MPQ COMPANY, '" + name + "'")

    @property
    def operator_name(self) -> str:
        return self.query("QMPQ OPERATOR")

    @operator_name.setter
    def operator_name(self, name: str):
        return self._command("MPQ OPERATOR, '" + name + "'")

    @property
    def contact_info(self) -> str:
        return self.query("QMPQ CONTACT")

    @contact_info.setter
    def contact_info(self, info: str):
        return self._command("MPQ CONTACT, '" + info + "'")

    @property
    def site_info(self) -> str:
        return self.query("QMPQ SITE")

    @site_info.setter
    def site_info(self, site: str):
        return self._command("MPQ SITE, '" + site + "'")

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

    @property
    def primary_value(self) -> float:
        return float(self.primary_measurement()["value"])

    def QDDA(self):
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
        #     'prim_function': get_map_value('primfunction', current_bytes, 0),
        #     'sec_function': get_map_value('secfunction', current_bytes, 2),
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

    def QRSI(self) -> None:
        """
        This is the data supporting an automated recording of measurements
        made by Fluke 28X the new firmware supports over a dozen 'recordings'
        each of which has its own identifying number that is shown in the
        display when viewing memory on the meter. In QRSI use 0-## with ##
        representing the last recording, not the "identifying number" IOW:
        there are 0 to nn slots holding recordings that might have YMMV
        identifiers. Fluke is clever with this. """

        raise NotImplementedError("Not yet available.")

        # ser.write(('qrsi 14' + '\r').encode('utf-8'))
        # ser.read(2) # the OK 0 and CR
        # data = (ser.read(999)) #.decode('utf-8'))
        # for i in range(0 , len(data)):
        #     print (str(i)+','+str((data[i])))
        #     #print (str((data[i])))
        # pass

    def QSRR(self) -> None:
        """(QSRR = Query Saved Recorded Readings)

        QSRR is reported to be the function that can access individual
        "samples" in a recording, presumably with the actual recording
        identifier obtained from QRSI. I have not been successful in
        accessing.
        """

        raise NotImplementedError("Not yet available.")
        # ser.write((('qsrr 5, 0').encode('utf-8')))
        # ser.write(149)
        # ser.write(('\r').encode('utf-8'))
        # if ser.read(2): # the OK 0 and CR
        #     data = (ser.read(999))  # .decode('utf-8'))
        #     print(data)
        #     for i in range(0, len(data)):
        #         print(str(i)+','+str((data[i])))
        #         # print (((data[i])))
        # return

    def QSMR(self):
        """(QSMR = Query Saved Measurement(?) Readings)"""
        # Saved Measurement
        # res = meter_command('qsmr ' + idx)
        # reading_count = get_u16(res, 36)

        # if len(res) < reading_count * 30 + 38:
        #     raise ValueError(
        #         'By app: qsmr parse error, expected at least %d bytes, got
        #               %d' % (reading_count * 30 + 78, len(res)))

        # return {'[seq_no': get_u16(res, 0),
        #         'un1': get_u16(res, 2),  # 32 bit?
        #         'prim_function': get_map_value('primfunction', res, 4),
        #         'sec_function': get_map_value('secfunction', res, 6),
        #         'auto_range': get_map_value('autorange', res, 8),
        #         'unit': get_map_value('unit', res, 10),
        #         'range_max': get_double(res, 12),
        #         'unit_multiplier': get_s16(res, 20),
        #         'bolt': get_map_value('bolt', res, 22),
        #         'un4': get_u16(res, 24),  # ts?
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

    def QPSI(self):
        # Saved Peak data?
        pass

    def QMMSI(self):
        # Saved min/max
        pass

    def QSLS(self):
        out = self.query("QSLS").split(",")
        return {"nb_recordings":   int(out[0]),
                "nb_min_max":      int(out[1]),
                "nb_peak":         int(out[2]),
                "nb_measurements": int(out[3])}

    def QueryLCDBitMap(self) -> ImageFile.ImageFile:
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
        # the opening 1018 bytes. This command includes a 2.5 second delay to
        # ensure that the command has time to complete as it is definitely not
        # instantaneous.
        img: bytes = self._command("QLCDBM 0", 2.5)
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

    def QSAVNAME(self):
        """ Query Save Names """
        pass
        # for i in range(1, 9):
        #     cmd = 'qsavname ' + str(i - 1) + '\r'
        #     res = meter_command(cmd)
        #     print(i, res[0].split('\r')[0], sep=sep)

    def _read_u16(self, input_str: str, offset: int) -> int:

        if offset > 0:
            endian: str = input_str[offset + 1:offset - 1:-1]
        else:
            endian: str = input_str[offset + 1::-1]

        return int(unpack('!H', endian)[0])  # type: ignore

    def press_button(
            self,
            button: Literal["HOLD", "ONOFF", "MINMAX", "F1", "UP", "RANGE",
                            "F2", "DOWN", "INFO", "F3", "LEFT", "BACKLIGHT",
                            "F4", "RIGHT"]):

        # Ensure that the button is one of the available options within the
        # multimeter to be pressed.
        if button not in self._buttons:
            raise ValueError("Invalid choice of button.")

        # Send the command to press the button to the multimeter.
        self._command("PRESS " + button)


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
    f.QueryLCDBitMap()
    pass
