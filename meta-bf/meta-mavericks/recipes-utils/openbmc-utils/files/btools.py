#!/usr/bin/python
#
# File is the tool for bringup of tofino chipset on Mavericks and Montara.
#
import sys
import os
import getopt
import subprocess
import os.path
from time import sleep

#
# btool usage for modules. Individual module usage is printed separately
#
def usage():

    print " "
    print "USAGE: "
    print "./btools.py --<[device]/help>"
    print "[device]"
    print "          PSU  => PFE1100 power supply unit"
    print "          UCD  => UCD90120A power supply sequencer"
    print "          IR   => Multiphase Controller"
    print "          TMP  => Temperature Sensors"
    print "Eg:"
    print "./btools.py --PSU help"
    print "./btools.py --UCD help"
    print "./btools.py --IR help"
    print "./btools.py --help"

    return
#
# Usage for PSU related arguments
#
def error_psu_usage():
    print " "
    print "USAGE: "
    print "./btools.py --PSU <power supply number> r v              => input voltage"
    print "                     <1 - 2>            r vo             => output voltage"
    print "                                        r i              => current"
    print "                                        r p              => power"
    print "                                        r ld             => load sharing"
    print "                                        r fspeed         => fan speed"
    print "                                        r ffault         => fan fault"
    print "                                        r presence       => power supply presence"
    print "                                        r sts_in_power   => power input status"
    print "                                        r sts_op_power   => power output status"
    print " "
    print "./btools.py --PSU 1 r v   => Read input voltage for power supply 1"

#
# Presence and power status is read from CPLD
#
def psu_cpld_features(power_supply, feature):

    cpld_dev = "/sys/class/i2c-adapter/i2c-12/12-0031/"
    cmd = "cat"

    if feature == "presence":
        if power_supply == 1:
            path = cpld_dev + "psu1_present"
        elif power_supply == 2:
            path = cpld_dev + "psu2_present"
        else:
            error_psu_usage()
            return
    elif feature == "sts_in_power":
        if power_supply == 1:
            path = cpld_dev + "psu1_in_pwr_sts"
        elif power_supply == 2:
            path = cpld_dev + "psu2_in_pwr_sts"
        else:
            error_psu_usage()
            return
    elif feature == "sts_op_power":
        if power_supply == 1:
            path = cpld_dev + "psu1_output_pwr_sts"
        elif power_supply == 2:
            path = cpld_dev + "psu2_output_pwr_sts"
        else:
            error_psu_usage()
            return
    else:
        error_psu_usage()
        return

    try:
        output = subprocess.check_output([cmd, path])
    except subprocess.CallProcessError as e:
        print e
        print "Error while executing psu cpld feature commands"
        return

    if feature == "presence":
        res = int(output, 16)
        if res == 0:
            print "Power supply %s present" % power_supply
            return 0
        else:
            print "Power supply %s not present" % power_supply
            return 1
    elif feature == "sts_in_power" or feature == "sts_op_power":
        # catching only first 3 characters of output
        res = int(output[:3], 16)
        if res == 0:
            print "Power supply status: BAD"
        elif res == 1:
            print "Power supply status: OK"
        else:
            print "Error while reading power supply status"
    return

#
# Function reads power supplies output voltage
#
def psu_read_output_voltage(power_supply):

    PSU_I2C_BUS = "7"
    PSU_I2C_READ_VOUT = "0x8b"

    if power_supply == 1:
        PSU_I2C_ADDR = "0x59"
    else:
        PSU_I2C_ADDR = "0x5a"

    try:
        get_cmd = "i2cget"
        output = subprocess.check_output([get_cmd, "-f", "-y", PSU_I2C_BUS,
                                     PSU_I2C_ADDR, PSU_I2C_READ_VOUT, "w"])
    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while processing output for PSU %d " % power_supply
        return

    # From PFE specs READ_VOUT1
    PSU_VOLTAGE_LN_FMT = 0x1 << 6

    # 11 bits are usable
    output = int(output, 16) & 0x7ff

    output = float(output) / PSU_VOLTAGE_LN_FMT

    print "Output Voltage  %.1fV" % output

    return

#
# Function is retrive current withdrawn on both power supplies
#
def psu_read_load_sharing():

    PSU_I2C_BUS = "7"
    PSU_I2C_READ_IOUT = "0x8C"

    try:
        #Read 1st power supply
        PSU_I2C_ADDR = "0x59"
        get_cmd = "i2cget"
        output1 = subprocess.check_output([get_cmd, "-f", "-y", PSU_I2C_BUS,
                                          PSU_I2C_ADDR, PSU_I2C_READ_IOUT, "w"])

        PSU_I2C_ADDR = "0x5a"
        output2 = subprocess.check_output([get_cmd, "-f", "-y", PSU_I2C_BUS,
                                          PSU_I2C_ADDR, PSU_I2C_READ_IOUT, "w"])

    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while processing load sharing for PSU"
        return

    # From PFE specs READ_IOUT1
    PSU_CURRENT_LN_FMT = 0x1 << 3

    # 11 bits are usable
    output1 = int(output1, 16) & 0x7ff
    output1 = float(output1) / PSU_CURRENT_LN_FMT

    output2 = int(output2, 16) & 0x7ff
    output2 = float(output2) / PSU_CURRENT_LN_FMT

    print "Power Supply 1 output current  %.3f amp" % output1
    print "Power Supply 2 output current  %.3f amp" % output2

    return

#
#open I2C sw before pfe devices and then load drivers
#
def psu_init():

    #check if pfe1100 driver is loaded properly
    if os.path.isfile("/sys/class/i2c-adapter/i2c-7/7-0059/in1_input"):
        return

    try:
        cmd = "i2cset"
        I2C_ADDR = "0x70"
        I2C_BUS = "7"
        OPCODE = "0x3"

        # Open I2C swtich for PFE devices
        #i2cset -f -y 7 0x70 0x3
        subprocess.check_output([cmd, "-f", "-y", I2C_BUS, I2C_ADDR, OPCODE])

        # remove pfe1100 driver
        subprocess.check_output(["rmmod", "pfe1100"])

        # load driver for both devices
        subprocess.check_output(["modprobe", "pfe1100"])

    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while initializing PSU"
        return

#function just for power supply check
def psu_check_pwr_presence(power_supply):

  psu_init()

  r = psu_cpld_features(power_supply, "presence")

  return r

#
# Function to handle PSU related requests
#
def psu(argv):

    i2c_dev = "/sys/class/i2c-adapter/i2c-7/7-00"

    arg_psu = argv[2:]

    if arg_psu[0] == "help" or arg_psu[0] == "h":
        error_psu_usage()
        return

    if arg_psu[0] != "1" and arg_psu[0] != "2":
        error_psu_usage()
        return

    psu_init()

    # Mapping i2c bus address according to power supply number
    if arg_psu[0] == "1":
        power_supply = 1
        ps = "59/"
    elif arg_psu[0] == "2":
        power_supply = 2
        ps = "5a/"

    if arg_psu[1] == "r":
        cmd = "cat"
    else:
        error_psu_usage()
        return

    if arg_psu[2] == "v":
        val = "in1_input"
        s = "V"
    elif arg_psu[2] == "i":
        val = "curr1_input"
        s = "mA"
    elif arg_psu[2] == "p":
        val = "power1_input"
        s = "mW"
    elif arg_psu[2] == "fspeed":
        val = "fan1_input"
        s = "rpm"
    elif arg_psu[2] == "ffault":
        val = "fan1_fault"
        s = "ffault"
    elif arg_psu[2] == "presence":
        psu_cpld_features(power_supply, "presence")
        return
    elif arg_psu[2] == "sts_in_power":
        psu_cpld_features(power_supply, "sts_in_power")
        return
    elif arg_psu[2] == "sts_op_power":
        psu_cpld_features(power_supply, "sts_op_power")
        return
    elif arg_psu[2] == "vo":
        psu_read_output_voltage(power_supply)
        return
    elif arg_psu[2] == "ld":
        psu_read_load_sharing()
        return
    else:
        error_psu_usage()
        return

    path = i2c_dev + ps + val

    try:
        output = subprocess.check_output([cmd, path])
    except subprocess.CallProcessError as e:
        print e
        print "Error while executing psu i2c command "
        return

    if s == "V":
        print "{}{}".format(float(output) / 1000, "V")             # convert milli volts to volts
    elif s == "mA":
        print "{}{}".format(float(output), "mA")                   # current is in milli Amperes
    elif s == "mW":
        print "{}{}".format(float(output) / 1000 , "mW")           # Power in milli watts
    elif s == "rpm":
        print "{}{}".format(int(output), "rpm")                    # Speed of FAN
    elif s == "ffault":
        print "{}".format(int(output))
    return

#
# Usage for UCD device
#
def error_ucd_usage():

    print " "
    print "Usage:"
    print "./btools.py --UCD sh v     => Show Voltage of all rails"
    print "                  fault    => Show Voltage fault/warnings of all rails"
    print "                  set_margin  <rail number> <margin>"
    print "                                 <1 - 12>    l /h /n"
    print "                                             l => low"
    print "                                             h => high"
    print "                                             n => none"

    print "./btools.py --UCD sh v"
    print "./btools.py --UCD set_margin 5 l"
    print " "

#
# Reads voltage faults on all rails
#
def ucd_rail_voltage_fault():

    i = 1

    UCD_I2C_BUS = "2"
    UCD_I2C_ADDR = "0x34"
    UCD_STATUS_VOUT_OP = "0x7A"
    UCD_PAGE_OP = "0x00"

    print " "
    print " RAIL      Voltage Warnings"

    # Parse 1 to 12 voltage rails
    for i in range(0, 12):

        try:
            # i2cset -f -y 2 0x34 0x00 i
            set_cmd = "i2cset"
            output = subprocess.check_output([set_cmd, "-f", "-y", UCD_I2C_BUS,
                                     UCD_I2C_ADDR, UCD_PAGE_OP, str(hex(i))])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cset for rail %.2d " % i
            continue

        try:
            # i2cget -f -y 2 0x34 w
            get_cmd = "i2cget"
            output = subprocess.check_output([get_cmd, "-f", "-y", UCD_I2C_BUS,
                                               UCD_I2C_ADDR, UCD_STATUS_VOUT_OP])

        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cget for rail %.2d " % i
            continue


        o = int(output, 16)

        fault_warnings = ""

        if o == 0:
            fault_warnings = "No fault/warning"
        else:
            if o & 0x10:
                fault_warnings = fault_warnings + "Under Voltage Fault,"

            if o & 0x20:
                fault_warnings = fault_warnings + "Under Voltage Warning,"

            if o & 0x40:
                fault_warnings = fault_warnings + "Over Voltage Warning,"

            if o & 0x80:
                fault_warnings = fault_warnings + "Over Voltage Fault,"

        print "  %.2d         %s" % (i + 1, fault_warnings)

    print " "

    return

#
# Displays all rails voltages
#
def ucd_rail_voltage():

    i = 1

    UCD_I2C_BUS = "2"
    UCD_I2C_ADDR = "0x34"
    UCD_READ_OP = "0x8b"
    UCD_PAGE_OP = "0x00"
    UCD_VOUT_MODE_OP = "0x20"

    print " "
    print " RAIL      Voltage(V)"

    # Parse 1 to 12 voltage rails
    for i in range(0, 12):

        try:
            # i2cset -f -y 2 0x34 0x00 i
            set_cmd = "i2cset"
            output = subprocess.check_output([set_cmd, "-f", "-y", UCD_I2C_BUS,
                                     UCD_I2C_ADDR, UCD_PAGE_OP, str(hex(i))])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cset for rail %.2d " % i
            continue

        try:
            # i2cget -f -y 2 0x34 w
            get_cmd = "i2cget"
            mantissa = subprocess.check_output([get_cmd, "-f", "-y", UCD_I2C_BUS,
                                               UCD_I2C_ADDR, UCD_READ_OP, "w"])

        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cget for rail %.2d " % i
            continue

        try:
            # i2cget -f -y 2 0x34 0x20
            get_cmd = "i2cget"
            exponent = subprocess.check_output([get_cmd, "-f", "-y", UCD_I2C_BUS,
                                               UCD_I2C_ADDR, UCD_VOUT_MODE_OP])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cget for rail %.2d " % i
            continue

        # 2 ^ exponent
        # exponent is 5 bit signed value. Thus calculating first exponent.
        # It is based on UCD90120A device spec section 2.2
        exp = int(exponent, 16) | ~0x1f
        exp = ~exp + 1
        div = 1 << exp

        mantissa = int(mantissa, 16)

        print "  %.2d         %.3f" % (i + 1, float(mantissa) / float(div))

    print " "

    return

#
# Functions set the voltage margins
#
def ucd_voltage_margin(arg):

    UCD_I2C_BUS = "2"
    UCD_I2C_ADDR = "0x34"
    UCD_LOW_MARGIN_OP = "0x18"
    UCD_HIGH_MARGIN_OP = "0x28"
    UCD_NONE_MARGIN_OP = "0x08"
    UCD_PAGE_OP = "0x00"
    UCD_MARGIN_OP = "0x01"

    if len(arg) is not 3:
        error_ucd_usage()
        return

    if not 1 <= int(arg[1]) <= 12:
        error_ucd_usage()
        return

    if arg[2] == "l":
        opcode = str(UCD_LOW_MARGIN_OP)
    elif arg[2] == "h":
        opcode = str(UCD_HIGH_MARGIN_OP)
    elif arg[2] == "n":
        opcode = str(UCD_NONE_MARGIN_OP)
    else:
        error_ucd_usage()
        return


    # Rail number mapping starts from 1
    # But UCD understand from 0. Thus reducing 1
    rail_number = int(arg[1]) - 1

    try:

        set_cmd = "i2cset"
        output = subprocess.check_output([set_cmd, "-f", "-y", UCD_I2C_BUS,
                                         UCD_I2C_ADDR, UCD_PAGE_OP, str(rail_number)])

    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while processing i2cset for rail %.2d " % (rail_number + 1)
        return

    try:

        set_cmd = "i2cset"
        output = subprocess.check_output([set_cmd, "-f", "-y", UCD_I2C_BUS,
                                         UCD_I2C_ADDR, UCD_MARGIN_OP, opcode])
    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while processing i2cset for rail %.2d " % (rail_number + 1)
        return

    try:

        set_cmd = "i2cget"
        output = subprocess.check_output([set_cmd, "-f", "-y", UCD_I2C_BUS,
                                         UCD_I2C_ADDR, UCD_MARGIN_OP])

    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while processing i2cset for rail %.2d " % (rail_number + 1)
        return

    print "Voltage margining done"

    return

#
# Dispatches UCD requests
#
def ucd(argv):

    arg_ucd = argv[2:]

    if arg_ucd[0] == "help" or arg_ucd[0] == "h":
        error_ucd_usage()
        return

    if arg_ucd[0] == "sh":
        ucd_rail_voltage()
    elif arg_ucd[0] == "set_margin":
        ucd_voltage_margin(arg_ucd)
    elif arg_ucd[0] == "fault":
        ucd_rail_voltage_fault()
    else:
        error_ucd_usage()
        return

    return

def ir_voltage_show_montara():

    IR_I2C_BUS = "0x1"
    IR_PMBUS_ADDR = {1: "0x70", 2: "0x72", 3: "0x77"}
    IR_VOUT_MODE_OP = "0x20"
    IR_READ_VOUT_OP = "0x8b"
    IR_READ_IOUT_OP = "0x8c"
    string ={1: "VDD", 2: "AVDD", 3: "QSFP"}

    for i in range(1, 4):

        try:
            # i2cget -f -y 1 0x70 0x8b w
            get_cmd = "i2cget"
            exponent = subprocess.check_output([get_cmd, "-f", "-y", IR_I2C_BUS,
                                     IR_PMBUS_ADDR.get(i), IR_VOUT_MODE_OP, "w"])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing VOUT_MODE for IR "
            continue

        try:
            # i2cget -f -y 1 0x70 0x8b w
            get_cmd = "i2cget"
            mantissa = subprocess.check_output([get_cmd, "-f", "-y", IR_I2C_BUS,
                                         IR_PMBUS_ADDR.get(i), IR_READ_VOUT_OP, "w"])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cget for IR "
            continue

        # 2 ^ exponent
        # exponent is 5 bit signed value. Thus calculating first exponent.
        exp = int(exponent, 16) | ~0x1f
        exp = ~exp + 1
        div = 1 << exp

        mantissa = int(mantissa, 16)

        v = (float(mantissa)/float(div))

        # As referred by hardware spec QSFP voltage need to be * 2
        if i == 3:
            v = v * 2

        # find current
        try:
            # i2cget -f -y 1 0x70 0x8c w
            get_cmd = "i2cget"
            mantissa = subprocess.check_output([get_cmd, "-f", "-y", IR_I2C_BUS,
                                         IR_PMBUS_ADDR.get(i), IR_READ_IOUT_OP, "w"])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cget for IR "
            continue

        m = int(mantissa, 16) & 0x07ff

        # 2 ^ exponent
        # exponent is 5 bit signed value. Thus calculating first exponent.
        exp = int(mantissa, 16) & 0xf800
        exp = exp >> 11
        exp = ~exp + 1
        exp = exp & 0x1f
        div = 1 << exp

        amp = (float(m)/float(div))

        print "IR %-*s       %.3f V    %.3f A      %.3f W" % (15, string.get(i), v, amp, (v * amp))

    return

#
# Mavericks need i2c switch to be opened for reading IR
#
def ir_open_i2c_switch():

    IR_I2C_SW_BUS = "9"
    IR_I2C_SW_ADDR = "0x70"

    try:
        get_cmd = "i2cget"
        output = subprocess.check_output([get_cmd, "-f", "-y",
                                          IR_I2C_SW_BUS,
                                          IR_I2C_SW_ADDR])

        output = int(output, 16)

        # opening i2c switch for 0x08, 0x09, 0x0c
        res = output | 0x7
        set_cmd = "i2cset"
        o = subprocess.check_output([set_cmd, "-f", "-y",
                                    IR_I2C_SW_BUS,
                                    IR_I2C_SW_ADDR, str(res)])

    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while processing opening i2c switch" \
              " on mavericks upper board"

    return output

#
# Restoring the i2c switch state
#
def ir_restore_i2c_switch(res):

    IR_I2C_SW_BUS = "9"
    IR_I2C_SW_ADDR = "0x70"

    try:
        set_cmd = "i2cset"
        o = subprocess.check_output([set_cmd, "-f", "-y",
                                    IR_I2C_SW_BUS,
                                    IR_I2C_SW_ADDR, str(res)])

    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while processing restoring i2c switch" \
              " on mavericks upper board"

    return

def ir_voltage_show_mavericks():

    a = ir_open_i2c_switch()

    UPPER_IR_I2C_BUS = "0x9"
    UPPER_IR_PMBUS_ADDR = {1: "0x40", 2: "0x74", 3: "0x71"}
    IR_VOUT_MODE_OP = "0x20"
    IR_READ_VOUT_OP = "0x8b"
    IR_READ_IOUT_OP = "0x8c"
    string = {1: "VDD_CORE", 2: "AVDD", 3: "QSFP_UPPER"}

    for i in range(1, 4):

        try:
            # i2cget -f -y 1 0x70 0x20 w
            get_cmd = "i2cget"
            exponent = subprocess.check_output([get_cmd, "-f", "-y", UPPER_IR_I2C_BUS,
                                     UPPER_IR_PMBUS_ADDR.get(i), IR_VOUT_MODE_OP, "w"])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing VOUT_MODE for UPPER IR "
            continue

        try:
            # i2cget -f -y 1 0x70 0x8b w
            get_cmd = "i2cget"
            mantissa = subprocess.check_output([get_cmd, "-f", "-y", UPPER_IR_I2C_BUS,
                                         UPPER_IR_PMBUS_ADDR.get(i), IR_READ_VOUT_OP, "w"])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cget for UPPER IR "
            continue

        # 2 ^ exponent
        # exponent is 5 bit signed value. Thus calculating first exponent.
        exp = int(exponent, 16) | ~0x1f
        exp = ~exp + 1
        div = 1 << exp

        mantissa = int(mantissa, 16)

        v = (float(mantissa)/float(div))

        # As referred by hardware spec QSFP voltage need to be * 2
        if i == 3:
            v = v * 2

        # find current
        try:
            # i2cget -f -y 1 0x70 0x8c w
            get_cmd = "i2cget"
            mantissa = subprocess.check_output([get_cmd, "-f", "-y", UPPER_IR_I2C_BUS,
                                        UPPER_IR_PMBUS_ADDR.get(i), IR_READ_IOUT_OP, "w"])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cget for IR "
            continue

        m = int(mantissa, 16) & 0x07ff

        # 2 ^ exponent
        # exponent is 5 bit signed value. Thus calculating first exponent.
        exp = int(mantissa, 16) & 0xf800
        exp = exp >> 11
        exp = ~exp + 1
        exp = exp & 0x1f
        div = 1 << exp

        amp = (float(m)/float(div))

        print "IR %-*s       %.3f V    %.3f A      %.3f W" % (15, string.get(i), v, amp, (v * amp))

    ir_restore_i2c_switch(a)

    LOWER_IR_I2C_BUS = "0x1"
    LOWER_IR_PMBUS_ADDR = {1: "0x71", 2: "0x72"}
    lower_string = {1: "QSFP_LOWER", 2: "REPEATER"}

    for i in range(1, 3):

        try:
            # i2cget -f -y 1 0x70 0x8b w
            get_cmd = "i2cget"
            exponent = subprocess.check_output([get_cmd, "-f", "-y", LOWER_IR_I2C_BUS,
                                     LOWER_IR_PMBUS_ADDR.get(i), IR_VOUT_MODE_OP, "w"])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing VOUT_MODE for LOWER IR "
            continue

        try:
            # i2cget -f -y 1 0x70 0x8b w
            get_cmd = "i2cget"
            mantissa = subprocess.check_output([get_cmd, "-f", "-y", LOWER_IR_I2C_BUS,
                                         LOWER_IR_PMBUS_ADDR.get(i), IR_READ_VOUT_OP, "w"])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cget for LOWER IR "
            continue

        # 2 ^ exponent
        # exponent is 5 bit signed value. Thus calculating first exponent.
        exp = int(exponent, 16) | ~0x1f
        exp = ~exp + 1
        div = 1 << exp

        mantissa = int(mantissa, 16)

        v = (float(mantissa)/float(div)) * 2

        # find current
        try:
            # i2cget -f -y 1 0x70 0x8c w
            get_cmd = "i2cget"
            mantissa = subprocess.check_output([get_cmd, "-f", "-y", LOWER_IR_I2C_BUS,
                                        LOWER_IR_PMBUS_ADDR.get(i), IR_READ_IOUT_OP, "w"])
        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cget for LOWER IR "
            continue

        m = int(mantissa, 16) & 0x07ff

        # 2 ^ exponent
        # exponent is 5 bit signed value. Thus calculating first exponent.
        exp = int(mantissa, 16) & 0xf800
        exp = exp >> 11
        exp = ~exp + 1
        exp = exp & 0x1f
        div = 1 << exp

        amp = (float(m)/float(div))

        print "IR %-*s       %.3f V    %.3f A      %.3f W" % (15, lower_string.get(i), v, amp, (v * amp))


    return

# IR utility usage
def error_ir_usage():

    print ""
    print "Usage:"
    print "./btools.py --IR sh v <mavericks/montara>         => Show IR voltages "
    print "./btools.py --IR set <mavericks/montara> <margin>        <voltage rail>  => Set IR voltages margin"
    print "                                           l = low margin       AVDD                   "
    print "                                           h = high margin      VDD_CORE               "
    print "                                           n = normal           QSFP_UPPER             "
    print "                                                                QSFP_LOWER             "
    print "                                                                REPEATER               "
    return

def read_vout(rail, I2C_BUS, I2C_ADDR):

    IR_VOUT_MODE_OP = "0x20"
    IR_READ_VOUT_OP = "0x8b"

    try:
      # i2cget -f -y 1 0x70 0x20 w
      get_cmd = "i2cget"
      exponent = subprocess.check_output([get_cmd, "-f", "-y", I2C_BUS,
                                     I2C_ADDR, IR_VOUT_MODE_OP, "w"])
    except subprocess.CalledProcessError as e:
      print e
      print "Error occured while processing VOUT_MODE "

    try:
      # i2cget -f -y 1 0x70 0x8b w
      get_cmd = "i2cget"
      mantissa = subprocess.check_output([get_cmd, "-f", "-y", UPPER_IR_I2C_BUS,
                                         I2C_ADDR, IR_READ_VOUT_OP, "w"])
    except subprocess.CalledProcessError as e:
      print e
      print "Error occured while processing i2cget "

    # 2 ^ exponent
    # exponent is 5 bit signed value. Thus calculating first exponent.
    exp = int(exponent, 16) | ~0x1f
    exp = ~exp + 1
    div = 1 << exp

    mantissa = int(mantissa, 16)

    v = (float(mantissa)/float(div))

    print ("IR %s       %.3f V" % rail, v)

    return

def set_ir_voltage(mod, i2c_bus, i2c_addr, margin_cmd, margin_apply, voltage):

  IR_OPERATION = "0x1"

  try:
    # set voltage margin value in register
    set_cmd = "i2cset"
    o = subprocess.check_output([set_cmd, "-f", "-y",
                                i2c_bus, i2c_addr,
                                margin_cmd, voltage, 'w'])

    # execute operation 0x1 with voltage margin AOF
    set_cmd = "i2cset"
    o = subprocess.check_output([set_cmd, "-f", "-y",
                                i2c_bus, i2c_addr,
                                IR_OPERATION, margin_apply, 'w'])

  except subprocess.CalledProcessError as e:
    print e
    print "Error occured while setting %s voltage low margin" % mod

  read_vout(mod, i2c_bus, i2c_addr)

  return

def ir_voltage_set_mavericks(arg_ir):

    a = ir_open_i2c_switch()

    UPPER_IR_I2C_BUS = "0x9"
    UPPER_IR_PMBUS_ADDR = {1: "0x40", 2: "0x72", 3: "0x75"}
    string_upper = {1: "VDD_CORE", 2: "AVDD", 3: "QSFP_UPPER"}
    LOWER_IR_I2C_BUS = "0x1"
    LOWER_IR_PMBUS_ADDR = {1: "0x71", 2: "0x72"}
    lower_string = {1: "QSFP_LOWER", 2: "REPEATER"}

    IR_MARGIN_LOW_AOF_OP = "0x98"
    IR_MARGIN_HIGH_AOF_OP = "0xA8"
    IR_MARGIN_OFF = "0x80"
    IR_OPERATION = "0x1"

    IR_VOUT_MARGIN_HIGH = "0x25"
    IR_VOUT_MARGIN_LOW = "0x26"
    IR_VOUT_CMD = "0x21"


    if arg_ir[3] == "AVDD":

      VOLT_MARGIN_HIGH = "0x1E4"
      VOLT_MARGIN_LOW = "0x1B6"
      VOLT_NORMAL = "0x1B6"
      i2c_addr = UPPER_IR_PMBUS_ADDR.get(2)

      if arg_ir[2] == "l":
        margin_cmd = IR_VOUT_MARGIN_LOW
        margin_apply = IR_MARGIN_LOW_AOF_OP
        voltage = VOLT_MARGIN_LOW

      elif arg_ir[2] == "h":
        margin_cmd = IR_VOUT_MARGIN_HIGH
        margin_apply = IR_MARGIN_HIGH_AOF_OP
        voltage = VOLT_MARGIN_HIGH

      else:
        margin_cmd = VOLT_NORMAL
        margin_apply = IR_MARGIN_OFF
        voltage = IR_VOUT_CMD

      set_ir_voltage(arg_ir[3], UPPER_IR_I2C_BUS, i2c_addr, margin_cmd, margin_apply, voltage)

    elif arg_ir[3] == "VDD_CORE":

      VOLT_MARGIN_HIGH = "0x1A5"
      VOLT_MARGIN_LOW = "0x1B6"
      VOLT_NORMAL =  "0x1AE"
      i2c_addr = UPPER_IR_PMBUS_ADDR.get(1)

      if arg_ir[2] == "l":
        margin_cmd = IR_VOUT_MARGIN_LOW
        margin_apply = IR_MARGIN_LOW_AOF_OP
        voltage = VOLT_MARGIN_LOW

      elif arg_ir[2] == "h":
        margin_cmd = IR_VOUT_MARGIN_HIGH
        margin_apply = IR_MARGIN_HIGH_AOF_OP
        voltage = VOLT_MARGIN_HIGH

      else:
        margin_cmd = VOLT_NORMAL
        margin_apply = IR_MARGIN_OFF
        voltage = IR_VOUT_CMD

      set_ir_voltage(arg_ir[3], UPPER_IR_I2C_BUS, i2c_addr, margin_cmd, margin_apply, voltage)

    elif arg_ir[3] == "QSFP_UPPER":

      VOLT_MARGIN_HIGH = "0x376"
      VOLT_MARGIN_LOW = "0x323"
      VOLT_NORMAL =  "0x34d"
      i2c_addr = UPPER_IR_PMBUS_ADDR.get(3)

      if arg_ir[2] == "l":
        margin_cmd = IR_VOUT_MARGIN_LOW
        margin_apply = IR_MARGIN_LOW_AOF_OP
        voltage = VOLT_MARGIN_LOW

      elif arg_ir[2] == "h":
        margin_cmd = IR_VOUT_MARGIN_HIGH
        margin_apply = IR_MARGIN_HIGH_AOF_OP
        voltage = VOLT_MARGIN_HIGH

      else:
        margin_cmd = VOLT_NORMAL
        margin_apply = IR_MARGIN_OFF
        voltage = IR_VOUT_CMD

      set_ir_voltage(arg_ir[3], UPPER_IR_I2C_BUS, i2c_addr, margin_cmd, margin_apply, voltage)

    elif arg_ir[3] == "QSFP_LOWER":

      VOLT_MARGIN_HIGH = "0x376"
      VOLT_MARGIN_LOW = "0x323"
      VOLT_NORMAL =  "0x34d"
      i2c_addr = LOWER_IR_PMBUS_ADDR.get(1)

      if arg_ir[2] == "l":
        margin_cmd = IR_VOUT_MARGIN_LOW
        margin_apply = IR_MARGIN_LOW_AOF_OP
        voltage = VOLT_MARGIN_LOW

      elif arg_ir[2] == "h":
        margin_cmd = IR_VOUT_MARGIN_HIGH
        margin_apply = IR_MARGIN_HIGH_AOF_OP
        voltage = VOLT_MARGIN_HIGH

      else:
        margin_cmd = VOLT_NORMAL
        margin_apply = IR_MARGIN_OFF
        voltage = IR_VOUT_CMD

      set_ir_voltage(arg_ir[3], LOWER_IR_I2C_BUS, i2c_addr, margin_cmd, margin_apply, voltage)

    elif arg_ir[3] == "REPEATER":

      VOLT_MARGIN_HIGH = "0x2A0"
      VOLT_MARGIN_LOW = "0x260"
      VOLT_NORMAL =  "0x280"
      i2c_addr = LOWER_IR_PMBUS_ADDR.get(2)

      if arg_ir[2] == "l":
        margin_cmd = IR_VOUT_MARGIN_LOW
        margin_apply = IR_MARGIN_LOW_AOF_OP
        voltage = VOLT_MARGIN_LOW

      elif arg_ir[2] == "h":
        margin_cmd = IR_VOUT_MARGIN_HIGH
        margin_apply = IR_MARGIN_HIGH_AOF_OP
        voltage = VOLT_MARGIN_HIGH

      else:
        margin_cmd = VOLT_NORMAL
        margin_apply = IR_MARGIN_OFF
        voltage = IR_VOUT_CMD

      set_ir_voltage(arg_ir[3], LOWER_IR_I2C_BUS, i2c_addr, margin_cmd, margin_apply, voltage)

    else:
        error_ir_usage()

    ir_restore_i2c_switch(a)

    return

def ir(argv):

    arg_ir = argv[2:]

    if arg_ir[0] == "help" or arg_ir[0] == "h" or len(arg_ir) != 3:
        error_ir_usage()
        return

    if arg_ir[0] == "sh":
        if arg_ir[2] == "Mavericks" or arg_ir[2] == "mavericks" :
            ir_voltage_show_mavericks()
        elif arg_ir[2] == "Montara" or arg_ir[2] == "montara" :
            ir_voltage_show_montara()
        else :
            error_ir_usage()
            return
    elif arg_ir[0] == "set":
        if arg_ir[1] == "Mavericks" or arg_ir[1] == "mavericks" :
            ir_voltage_set_mavericks(arg_ir)
        elif arg_ir[1] == "Montara" or arg_ir[1] == "montara" :
            ir_voltage_set_montara(arg_ir)
        else :
            error_ir_usage()
            return
    else:
        error_ir_usage()
        return

    return

#
# Temperature utility usage
#
def error_tmp_usage():

    print " "
    print "Usage:"
    print "./btools.py --TMP <board type> sh           => Show Temp"
    print "                  <board type>      Montara or Mavericks"
    print "Eg."
    print "./btools.py --TMP Montara sh        Show Temp sensors values on Montara"

    return

#
# Lower board temperature sensors. Board exists on Montara and Mavericks
#
def tmp_lower(board):

    i2c_dev = "/sys/class/i2c-adapter/i2c-3/3-00"

    tmp_sensor = {1: "48/temp1_input",
                  2: "49/temp1_input",
                  3: "4a/temp1_input",
                  4: "4b/temp1_input",
                  5: "4c/temp1_input"}

    cmd = "cat"

    if board == "Mavericks":
        x = 6
    else:
        x = 5

    for i in range(1, x):

        path = i2c_dev + tmp_sensor.get(i)
        try:

            output = subprocess.check_output([cmd, path])
            print " TMP SENSOR %.2d                  %.3f C" % (i,
                                                          float(output) / 1000)

        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while reading Temperature sensor %d " % i

    if board == "Montara":

        cmd = "i2cget"

        try:
            output = subprocess.check_output([cmd, "-f", "-y", "3", "0x4d",
                                             "0x00", "w"])
            output = int(output, 16)
            t = output & 0xff
            d = output & 0xfff00

            # if d is 0x80 means .0625 * 8(consider only fourth nibble 2 ^ 3)
            if d == 0x8000:
                t = float(t) + .500

            print " TMP SENSOR %.2d                  %.3f C" % (5, t)


            output = subprocess.check_output([cmd, "-f", "-y", "3",
                                             "0x4c", "0x00"])
            output = int(output, 16)
            print " TMP SENSOR MAX LOCAL           %.3f C" % output

            output = subprocess.check_output([cmd, "-f", "-y", "3",
                                             "0x4c", "0x01"])
            output = int(output, 16)
            print " TMP SENSOR MAX Tofino          %.3f C" % (output)

        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while reading Temperature sensor %d " % i

    return

#
# Upper board temperature sensors. It only exists in Mavericks
#
def tmp_upper():

    TMP75_I2C_BUS = "9"
    TMP75_I2C_ADDR = {1: "0x48", 2: "0x49", 3: "0x4a", 4: "0x4b"}
    TMP75_READ_OP = "0x00"

    for i in range(1, 5):

        try:

            get_cmd = "i2cget"
            output = subprocess.check_output([get_cmd, "-f", "-y",
                                             TMP75_I2C_BUS,
                                             TMP75_I2C_ADDR.get(i),
                                             TMP75_READ_OP, "w"])
            output = int(output, 16)

            t = output & 0xff
            d = output & 0xfff00

            # if d is 0x80 means .0625 * 8(consider only fourth nibble 2 ^ 3)
            if d == 0x8000:
                t = float(t) + .500

            print " TMP SENSOR UPPER %.2d            %.3f C" % (i, t)

        except subprocess.CalledProcessError as e:
            print e
            print "Error occured while processing i2cget for Tmp75 %.2d " % (i)


    TMP_MAX_I2C_BUS = "9"
    TMP_MAX_I2C_ADDR = "0x4c"
    TMP_MAX_READ_OP = "0x00"
    TMP_MAX_READ_EXT_OP = "0x01"

    try:
        get_cmd = "i2cget"
        output = subprocess.check_output([get_cmd, "-f", "-y",
                                          TMP_MAX_I2C_BUS,
                                          TMP_MAX_I2C_ADDR,
                                          TMP_MAX_READ_OP])
        output = int(output, 16)

        print " TMP SENSOR UPPER MAX LOCAL     %.2d.000 C" % (output)

        output = subprocess.check_output([get_cmd, "-f", "-y",
                                          TMP_MAX_I2C_BUS,
                                          TMP_MAX_I2C_ADDR,
                                          TMP_MAX_READ_EXT_OP])

        output = int(output, 16)

        print " TMP SENSOR UPPER MAX TOFINO    %.2d.000 C" % (output)

    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while processing i2cget for Tmp MAX sensor"

    return

#
# Mavericks need i2c switch to be opened for reading temp sensors
#
def tmp_open_i2c_switch():

    TMP_I2C_SW_BUS = "9"
    TMP_I2C_SW_ADDR = "0x70"

    try:
        get_cmd = "i2cget"
        output = subprocess.check_output([get_cmd, "-f", "-y",
                                          TMP_I2C_SW_BUS,
                                          TMP_I2C_SW_ADDR])

        output = int(output, 16)

        # opening i2c switch for 0x4a, 0x4b, 0x4c
        res = output | 0x10
        set_cmd = "i2cset"
        o = subprocess.check_output([set_cmd, "-f", "-y",
                                    TMP_I2C_SW_BUS,
                                    TMP_I2C_SW_ADDR, str(res)])

    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while processing opening i2c switch" \
              " on mavericks upper board"

    return output

#
# Restoring the i2c switch state
#
def tmp_restore_i2c_switch(res):

    TMP_I2C_SW_BUS = "9"
    TMP_I2C_SW_ADDR = "0x70"

    try:
        set_cmd = "i2cset"
        o = subprocess.check_output([set_cmd, "-f", "-y",
                                    TMP_I2C_SW_BUS,
                                    TMP_I2C_SW_ADDR, str(res)])

    except subprocess.CalledProcessError as e:
        print e
        print "Error occured while processing restoring i2c switch" \
              " on mavericks upper board"

    return

#
# Dispatching temperature sensor requests
#
def tmp(argv):

    if argv[2] == "help" or argv[2] == "h":
        error_tmp_usage()
        return

    if len(argv) != 4:
        error_tmp_usage()
        return

    if argv[3] != "sh":
        error_tmp_usage()
        return

    if argv[2] == "Montara" or argv[2] =="montara":
        tmp_lower("Montara")
    elif argv[2] == "Mavericks" or argv[2] == "mavericks":
        a = tmp_open_i2c_switch()
        tmp_lower("Mavericks")
        tmp_upper()
        tmp_restore_i2c_switch(a)
    else:
        error_tmp_usage()
        return

    return

def error_usage():
    print "Error in arguments passed. Please look at usage."
    usage()
    return

# Main function parses command line argument and call appropiate tool
def main(argv):

    lock_file = "/tmp/btools_lock"
    timeout_counter = 0

    try:
        opts, args = getopt.getopt(argv[1:], "hP:U:I:T:", ["help", "PSU=", "UCD=", "IR=", "TMP="])

        # No standard identifier.print the usage
        if len(opts) == 0:
            print "Number of invalid arguments %d " % len(args)
            error_usage()
            return

    except getopt.GetoptError:
        error_usage()
        return

    while os.path.isfile(lock_file):
        timeout_counter = timeout_counter + 1
        if timeout_counter >= 10:
	    # It's possible that the other process using the lock might have 
	    # malfunctioned. Hence explicitly delete the file and proceed
	    print "Some process didn't clean up the lock file. Hence explicitly cleaning it up and proceeding"
	    os.remove(lock_file)
	    break
        sleep(0.5)                  
                                    
    open(lock_file, "w+") 

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
        elif opt in ("-P", "--PSU"):
            psu(argv)
        elif opt in ("-U", "--UCD"):
            ucd(argv)
        elif opt in ("-I", "--IR"):
            ir(argv)
        elif opt in ("-T", "--TMP"):
            tmp(argv)
        else:
            error_usage()

    try:                            
         os.remove(lock_file)         
    except OSError:                      
         pass 

    return

if __name__ == '__main__':
    sys.exit(main(sys.argv))

