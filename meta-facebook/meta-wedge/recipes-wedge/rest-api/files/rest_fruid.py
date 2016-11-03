#!/usr/bin/env python
#
# Copyright 2014-present Facebook. All Rights Reserved.
#
# This program file is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program in a file named COPYING; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor,
# Boston, MA 02110-1301 USA
#


from ctypes import *

# Handler for FRUID resource endpoint
fru = CDLL("libwedge_eeprom.so")

class FRU(Structure):
	_fields_ = [ ("fbw_version", c_ubyte),
		       ("fbw_product_name", c_char * 13),
		       ("fbw_product_number", c_char * 10),
		       ("fbw_assembly_number", c_char * 15),
		       ("fbw_facebook_pcba_number", c_char * 15),
		       ("fbw_facebook_pcb_number", c_char * 15),
		       ("fbw_odm_pcba_number", c_char * 14),
		       ("fbw_odm_pcba_serial", c_char * 13),
		       ("fbw_production_state", c_ubyte),
		       ("fbw_product_version", c_ubyte),
		       ("fbw_product_subversion", c_ubyte),
		       ("fbw_product_serial", c_char * 13),
		       ("fbw_product_asset", c_char * 13),
		       ("fbw_system_manufacturer", c_char * 9),
		       ("fbw_system_manufacturing_date", c_char * 10),
		       ("fbw_pcb_manufacturer", c_char * 9),
		       ("fbw_assembled", c_char * 9),
		       ("fbw_local_mac", c_ubyte * 6),
		       ("fbw_mac_base", c_ubyte * 6),
		       ("fbw_dummy", c_char),
		       ("fbw_mac_size", c_ushort),
		       ("fbw_location", c_char * 9),
		       ("fbw_crc8", c_ubyte) ]

def get_fruid():
    myfru = FRU()
    p_myfru = pointer(myfru)
    fru.wedge_eeprom_parse(None, p_myfru)

    mac2str = lambda mac: ':'.join(['{:02X}'.format(b) for b in mac])

    import subprocess
    val = subprocess.Popen(['/usr/sbin/i2cset', '-f', '-y', '6', '0x51', '0x01', '0x00', 'i'], stdout=subprocess.PIPE).communicate()

    for num in range(0,11):
        val = subprocess.Popen(['/usr/sbin/i2cget', '-f', '-y', '6', '0x51'], stdout=subprocess.PIPE).communicate()
        temp = val[0][2], val[0][3]
        res = str(int(''.join(temp)) - 30)
        myfru.fbw_assembly_number += res

    return myfru.fbw_assembly_number    

    fruinfo = { "Version": myfru.fbw_version,
                "Product Name": myfru.fbw_product_name,
                "Product Part Number": myfru.fbw_product_number,
                "System Assembly Part Number": myfru.fbw_assembly_number,
                "Facebook PCBA Part Number": myfru.fbw_facebook_pcba_number,
                "Facebook PCB Part Number": myfru.fbw_facebook_pcb_number,
                "ODM PCBA Part Number": myfru.fbw_odm_pcba_number,
                "ODM PCBA Serial Number": myfru.fbw_odm_pcba_serial,
                "Product Production State": myfru.fbw_production_state,
                "Product Version": myfru.fbw_product_version,
                "Product Sub-Version": myfru.fbw_product_subversion,
                "Product Serial Number": myfru.fbw_product_serial,
                "Product Asset Tag": myfru.fbw_product_asset,
                "System Manufacturer": myfru.fbw_system_manufacturer,
                "System Manufacturing Date": myfru.fbw_system_manufacturing_date,
                "PCB Manufacturer": myfru.fbw_pcb_manufacturer,
                "Assembled At": myfru.fbw_assembled,
                "Local MAC": mac2str(myfru.fbw_local_mac),
                "Extended MAC Base": mac2str(myfru.fbw_mac_base),
                "Extended MAC Address Size": myfru.fbw_mac_size,
                "Location on Fabric": myfru.fbw_location,
                "CRC8": hex((myfru.fbw_crc8))
                }

    result = {
                "Information": fruinfo,
                "Actions": [],
                "Resources": [],
             }

    return result
