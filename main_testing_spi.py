'''
OpenIMU SPI package version 26.0.13.
-pip install spidev3.4, 
-read package through SPI interface, OpenIMU330BI test on Pi3 board(Raspbian OS,Raspberry 3B+).
-Spi slave: OpenIMU 330 EVK
-Pins connection:
    Pi3                   330/300 evk
	miso        <==>      miso
	mosi        <==>      mosi
	sck         <==>      sck
	gpio(bcm4)  <==>      cs   black line
    gpio(bcm17) <==>      drdy red line
	gnd         <==>      gnd
    gpio(bcm27) <==>      nRST
@cek from Aceinna 20210710
'''

import os
import sys
import spidev
import time, math
import struct
import json
import traceback
try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("Error import RPi.GPIO!")
from OpenIMU_SPI_cek import *
from testcase_SPI import *

try: 
    module_name = "330BA"
    app_name = "IMU125"
    fw_num = '26.0.13'


    openimu_spi = SpiOpenIMU(target_module=module_name,drdy_status=True, fw=fw_num) 

    filename = ["_", openimu_spi.module,"_", app_name, "_", openimu_spi.fw_version]

    f = open("data" + "".join(filename) + '.txt', "w")
    str_config = f"module style:{openimu_spi.module}; drdy:{openimu_spi.drdy}; {app_name}_{openimu_spi.fw_version};\n"
    print(str_config)
    f.write(str_config) 
    print("Power on IMU !!!!!!!!")
    # time.sleep(1)
    with open('spi_config' + "".join(filename[:4]) + '.json') as json_data:
        spi_attribute = json.load(json_data)

    test_runner = test_case(spi_module=openimu_spi, spi_config=spi_attribute, recoredfile=f)
    test_runner.dev.power_reset()  #IMU331 NEED TO WAIT 1.26s after power on.
    
    # test_runner.recover_default_setting(save_config=True)

    test_runner.default_setting_check();
    test_runner.single_data_reading();

    # test_runner.burst_data_reading(burst_type="extended_vg_burst")
    # input('start burst')
    # while True:
    #     test_runner.burst_data_reading(burst_type="standard_burst")
        

    # test_runner.burst_data_reading(burst_type="extended_mag_burst")
    # input('start burst')
    # while True:
    #     if "330BA" in module_name or "331BI" in module_name:
    #         test_runner.burst_data_reading(burst_type="extended_time_burst") 
    input('start burst')
    while True:
        if "330BA" in module_name or "331BI" in module_name:
            test_runner.burst_data_reading(burst_type="extended_time_burst_hr") 
    

    # test_runner.setting_check_pwr_rst(save_config=False)
    # test_runner.setting_check_pwr_rst(save_config=True)

    # test_runner.single_register_setting_values()
    # # test_runner.single_register_setting_values(actual_measure=[0x37])
    # reg_list=[0x74, 0x75], 
    # reg_name = "orientation",
    # val_list=[0x0000, 0x0009, 0x0023, 0x002A, 0x0041, 0x0048, 0x0062, 0x006B, 0x0085, 
    #             0x008C, 0x0092, 0x009B, 0x00C4, 0x00CD, 0x00D3, 0x00DA, 0x0111, 0x0118, 
    #             0x0124, 0x012D, 0x0150, 0x0159, 0x0165, 0x016C, 0x1111
    #         ] 
    # test_runner.double_register_setting_values(reg_name,reg_list,val_list)

    # test_runner.detect_sf_gyro() #rotation 90deg, 200hz, sum of ryro_z = 18000 t1= 0.005


    # test_runner.recover_default_setting(save_config=True)


    input("finished")
    os._exit(0)
except Exception as e:
    print(e)
    traceback.print_exc()    
    print("stoped by customer!")



        
















