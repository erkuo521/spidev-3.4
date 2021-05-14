'''
OpenIMU SPI package version 0.2.0.
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
@cek from Aceinna 2019.11.4
'''

import os
import sys
import spidev
import time, math
import struct
import json
try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("Error import RPi.GPIO!")
from OpenIMU_SPI_cek import *
from testcase_SPI import *

openimu_spi = SpiOpenIMU(target_module="300ZI",drdy_status=True, fw='4.1.4') 

f = open("data_" + str(openimu_spi.module) + ".txt", "w")
str_config = "module style:{openimu_spi.module}; drdy:{openimu_spi.drdy};\n"
print(str_config)
f.write(str_config) 
input("Power on IMU !!!!!!!!")
time.sleep(2)  

with open('spi_config_' + openimu_spi.module + '.json') as json_data:
    spi_attribute = json.load(json_data)

test_runner = test_case(spi_module=openimu_spi, spi_config=spi_attribute, recoredfile=f)

test_runner.default_setting_check();
test_runner.single_data_reading();

input("finished")




openimu_spi = SpiOpenIMU(target_module="330BA",drdy_status=True, fw='26.0.8')   #set the module name and drdy status(enalbe or not)-----------------step: 1
burst_read, single_read, single_write = True, True, True  # set the read style, burst or single------------step:2

try:        
    if openimu_spi.drdy == False:  # when no drdy, default SPI ODR is 100HZ 
        time.sleep(0.01)
    # for i_wd in range(9,12):
    # for i_wd in [0x00, 0x03,0x04,0x05,0x06,0x30,0x40,0x50,0x60,0x0B, 0x0B]:
    # ori_list = [0x0000, 0x0009, 0x0023, 0x002A, 0x0041, 0x0048, 0x0062, 0x006B, 0x0085, 0x008C, 0x0092, 0x009B, 0x00C4, 0x00CD, 0x00D3, 
    #             0x00DA, 0x0111, 0x0118, 0x0124, 0x012D, 0x0150, 0x0159, 0x0165, 0x016C
    #             ]
    # ori_list = [0x0009, 0x016C]
    # for i_wd in ori_list:
    if single_read:
        read_name = [
                    "X_Rate", "Y_Rate", "Z_Rate", "X_Accel", "Y_Accel", "Z_Accel","X_Mag", "Y_Mag", "Z_Mag", "BOARD_TEMP", "RATE_TEMP", "DRDY_RATE", "ACCEL_LPF", "ACCEL_SCALE_FACTOR", "RATE_SCALE_FACTOR", 
                    "SN_1", "SN_2", "SN_3", "PRODUCT_ID", "MASTER_STATUS", "HW_STATUS", "SW_STATUS", "ACCEL_RANGE/RATE_RANGE", 
                    "ORIENTATION_MSB/ORIENTATION_LSB", "SAVE_CONFIG", "RATE_LPF", "HW_VERSION/SW_VERSION"
                    ]
        read_reg = [
                    0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x10, 0x12, 0x14, 0x16, 0x18, 0x37, 0x38, 0x46, 0x47, 
                    0x52, 0x54, 0x58, 0x56, 0x5A, 0x5C, 0x5E, 0x70, 0x74, 0x76, 0x78, 0x7E
                    ]  
        # read_name = ["ORIENTATION_MSB"]
        # read_reg = [0x74]
        for i in zip(read_name, read_reg):                
            read_value = openimu_spi.single_read(i[1])
            hex_value = hex(read_value)
            prt_list = [i[0], hex(i[1]), hex_value]
            print(prt_list)
            if 'Rate' in i[0]: 
                read_value /= 64
            elif 'Accel' in i[0]:
                read_value /= 4000
            elif 'Mag' in i[0]:
                read_value /= 16354
            elif 'TEMP' in i[0]:
                read_value = read_value*0.073111172849435 + 31.0
            str_temp = "{0:_<40s}0x{1:<5X} read value: 0d {2:<10} hex value: {3:<10s}\n".format(i[0], i[1], read_value, hex_value)
            print(str_temp)
            f.write(str(prt_list) + '\n' + str_temp) 
        
    if single_write:    
        while input('need write? y/n?') != 'y':
            pass                            
        write_name = ["packet rate", "Accel LPF", "orimsb", "orilsb", "Rate LPF", "save config"]
        write_reg = [0x37, 0x76]
        write_data = [0x01, 0x00]
        # write_name = ["ORIENTATION_LSB"]
        # write_reg = [0x75]
        # write_data = [0x02]    
        # write_data = [i_wd, i_wd]            
        # write_data = [i_wd & 0xFF]
        for j in zip(write_name, write_reg, write_data):    #start to write registers
            print("write_name:{0:<40s}, write address:0x{1:<5X}, wirte data:0x{2:<5X}".format(j[0], j[1], j[2]))            
            openimu_spi.single_write(j[1], j[2])
            time.sleep(0.5)
    # if single_read or single_write:
    #     break 
    while input('need burst read? y/n?') != 'y':
        pass  
    while burst_read: # not seting the ODR, if you use burst read, it will same with frequency of DRDY            
        if ('330BI' in openimu_spi.module) or ('330BA' in openimu_spi.module):
            # list_rate, list_acc = openimu_spi.burst_read(first_register=0x3E,subregister_num=8)     #input the read register and numbers of subregisters want to read together
            # str_burst = "time:{0:>10f};  gyro:{1:>25s};  accel:{2:>25s} \n".format(
            #     time.clock(), ", ".join([str(x) for x in list_rate]), ", ".join([str(x) for x in list_acc])
            #     )
            list_sts, list_rate, list_acc, list_temp, list_mag, list_deg, tmstamp = openimu_spi.burst_read(first_register=0x3F,subregister_num=10)     #input the read register and numbers of subregisters want to read together
            str_burst = "time:{0:>10f};  gyro:{1:>50s};  accel:{2:>50s}; timestamp:{3:>25s} \n".format(
                time.clock(), ", ".join([str(x) for x in list_rate]), ", ".join([str(x) for x in list_acc]), ", ".join([str(x) for x in tmstamp])
            )
            
        else:
            list_sts, list_rate, list_acc, list_temp, list_mag, list_deg, tmstamp= openimu_spi.burst_read(first_register=0x3D,subregister_num=11)
            str_burst = "time:{0:>20f};  status:{3:>20s} ; gyro:{1:>50s};  accel:{2:>40s}; temp:{4:>10s}; mag:{5:>20s}; deg:{6:>20s}\n".format(
                time.clock(), ", ".join([str(x) for x in list_rate]), ", ".join([str(x) for x in list_acc]), ", ".join([str(x) for x in list_sts]), 
                ", ".join([str(x) for x in list_temp]), ", ".join([str(x) for x in list_mag]), ", ".join([str(x) for x in list_deg])
                )
        print(str_burst)               
        f.write(str_burst)
        # input('next cycle')

    
except KeyboardInterrupt:
    f.close()
    print("stoped by customer!")
        




















    # polling mode reading spi interface, with drdy pin detection
    # try:
    #     while True:
    #         # GPIO.output(cs_channel,GPIO.LOW)
    #         # product_id = spi.xfer2([0x56,0x00,0x00,0x00],0,10)
    #         # GPIO.output(cs_channel,GPIO.HIGH)                     
    #         # print('id',product_id)            
    #         time.sleep(0.1)
            
    #         # if GPIO.event_detected(interrupt_channel):
    #         if True:
    #             time.sleep(0.5)
    #             GPIO.output(cs_channel,GPIO.LOW)
    #             # xfer2([value],speed_hz,delay_usec_cs), SPI bi-direction data transfer.
    #             # default 8 bits mode, if speed_hz set to zero means the maximun supported SPI clock.
    #             # delay_usec_cs is the cs hold delay
    #             resp = spi.xfer2([openimu_spi.burst_cmd_std,0x00,0x00,0x00,0x00,0x00,0x00,
    #                     0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],0,10)
    #             GPIO.output(cs_channel,GPIO.HIGH)
    #             #unit:degree per second
    #             x_rate = openimu_spi.combine_reg(resp[4],resp[5])/200
    #             y_rate = openimu_spi.combine_reg(resp[6],resp[7])/200
    #             z_rate = openimu_spi.combine_reg(resp[8],resp[8])/200
    #             #unit:mg
    #             x_acc = openimu_spi.combine_reg(resp[10],resp[11])/4
    #             y_acc = openimu_spi.combine_reg(resp[12],resp[13])/4
    #             z_acc = openimu_spi.combine_reg(resp[14],resp[15])/4
    #             print('g/a',x_rate,y_rate,z_rate,x_acc,y_acc,z_acc)
            
            
            
    # #write to register
    # time.sleep(0.5)
    # GPIO.output(cs_channel,GPIO.LOW)             
    # resp1 = spi.xfer2([0x80|0x50,0x23],0,10)
    # time.sleep(0.5)
    # GPIO.output(cs_channel,GPIO.HIGH) 

    # 0x56 OPEN300 ID: 0x30(48) 0x00(0) 
    # 0x56 OPEN330 ID: 0x33(48) 0x00(0)
    # 0x56 IMU381 ID:  0X38(56) 0x10(16)  


