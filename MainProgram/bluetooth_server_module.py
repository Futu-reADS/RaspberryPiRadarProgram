import queue
import time
import threading
import bluetooth
import math
import random
import socket
import subprocess       # for Raspberry Pi shutdown
import os

import datetime

import shared_variables as sv


class BluetoothServer:
    # run = True  # Argument for shuting down all loops at the same time with input from one device.

#     def __init__(self, list_of_variables_for_threads):
    def __init__(self):
        # List of all variables from main to class.
#         self.list_of_variables_for_threads = list_of_variables_for_threads

        self.shutdown_yet = sv.list_of_variables_for_threads["shutdown_yet"]
        print('self.shutdown_yet = ' + str(self.shutdown_yet))  # for debug
        self.terminate_yet = sv.list_of_variables_for_threads["terminate_yet"]
        self.is_measuring = sv.list_of_variables_for_threads["is_measuring"]

        self.go = sv.list_of_variables_for_threads["go"]
        # Bluetooth variables
        self.client_list = []         # list for each connected device, sockets
        self.address_list = []        # list for mac-adresses from each connected device
        # self.read_thread_list = []     # list for threads to recieve from each device
        self.host = ""
#         self.port = 1
        self.port = 22
        self.client = None
        # Setup server for bluetooth communication
        self.server = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.server.setblocking(0)  # Makes server.accept() non-blocking, used for "poweroff"
        # TEMP: Data from radar used to make sure data can be accepted between threads
        # Queue from radar class to test if queue communication work
        self.RR_final_queue = sv.list_of_variables_for_threads["RR_final_queue"]
        self.RTB_final_queue = sv.list_of_variables_for_threads["RTB_final_queue"]
        self.run_measurement = sv.list_of_variables_for_threads["run_measurement"]
        self.start_write_to_csv_time = sv.list_of_variables_for_threads["start_write_to_csv_time"]
        self.initiate_write_heart_rate = sv.list_of_variables_for_threads["initiate_write_heart_rate"]
        print('Bluetooth Socket Created')
        try:
            self.server.bind((self.host, self.port))
            print("Bluetooth Binding Completed")
        except:
            print("Bluetooth Binding Failed")

        # Can be accessed from main-program to wait for it to close by .join()
        self.connect_device_thread = threading.Thread(
            target=self.connect_device)  # Starts thread which accepts new devices
        self.connect_device_thread.start()

        self.f_hr_csv  = sv.list_of_variables_for_threads["f_hr_csv"]
        self.f_rr_csv  = sv.list_of_variables_for_threads["f_rr_csv"]
        self.f_rtb_csv = sv.list_of_variables_for_threads["f_rtb_csv"]
        self.f_bp_csv = sv.list_of_variables_for_threads["f_bp_csv"]
        self.measurement_start_time = sv.list_of_variables_for_threads["measurement_start_time"]

        self.filename_rec_csv = ''
        self.f_rec_csv = None
#         self.user_serial_number = 1  # 現時点では1固定(実際にはスマホから送ってもらう)
        self.user_serial_number = ''

    def app_data(self):  # The main loop which takes data from processing and sends data to all clients
        while self.go:
            pass
            # while len(self.client_list) == 0:
            #    time.sleep(1)
            #    continue
            # self.schmitt_to_app()
            # self.real_time_breating_to_app()
            # data = self.add_data(2)  # TEMP: Makes random data for testing of communication
            # data_pulse, data_breath = data.split(' ')  # Splits data in pulse and heart rate
            # self.write_data_to_app(data_pulse, 'heart rate')  # Sends pulse to app
            # self.write_data_to_app(data_breath, 'breath rate')  # Sends heart rate to app

    def schmitt_to_app(self):
        try:
            # TEMP: Takes data from Schmitt trigger
            while len(self.RR_final_queue) == 0 and self.go:
                time.sleep(0.001)
            schmitt_data = self.RR_final_queue.get_nowait()
            # print("got data from queue")
            self.write_data_to_app(schmitt_data, 'breath rate')
        # schmitt_data = ' BR ' + schmitt_data + ' '      # TODO ändra till RR istället för BR i appen också
        # print("made string")
        # self.send_data(schmitt_data)
        # print("sent data")
        except:
            print("timeout RR queue")

    def real_time_breating_to_app(self):
        try:
            # while self.RTB_final_queue.empty() and self.go:
            #    time.sleep(0.005)
            # TEMP: Takes data from filtered resp.rate
            real_time_breating_to_app = self.RTB_final_queue.get_nowait()
            # print("Real time breathing to app {}".format(real_time_breating_to_app))
            self.write_data_to_app(real_time_breating_to_app, 'real time breath')
            if not self.RR_final_queue.empty():
                schmitt_data = self.RR_final_queue.get_nowait()
                self.write_data_to_app(schmitt_data, 'breath rate')

        except:
            print(len(self.RR_final_queue))

    def connect_device(self):
        #os.system("echo 'power on\nquit' | bluetoothctl")  # Startup for bluetooth on rpi TODO
        thread_list = []  # List which adds devices
        self.server.listen(7)  # Amount of devices that can simultaniously recive data.
#         while self.go:
        while self.shutdown_yet:
            # Loop which takes listens for a new device, adds it to our list
            # and starts a new thread for listening on input from device
            try:
                c, a = self.server.accept()
            except:
#                 if self.go == False:
                if self.shutdown_yet == False:
                    break
                # print("Still accepting new phones" + str(error))
                continue
            self.client_list.append(c)
            self.address_list.append(a)
            # one thread for each connected device
            thread_list.append(threading.Thread(target=self.read_device))
            thread_list[-1].start()
            print(thread_list[-1].getName())
            print(thread_list[-1].isAlive())
            print("New client: ", a)

        print("Out of while True in connect device")
        # Gracefully close all device threads
        for thread in thread_list:
            print(str(thread.getName()) + str(thread.isAlive()))
            thread.join()
            print(str(thread.getName()) + " is closed")
        print("End of connect_device thread")

    def read_device(self):
        c = self.client_list[-1]  # Takes last added device and connects it.
        print(c)
        print(self.address_list[-1])
        try:
            filepath = '/media/futu-re/05E2-E73B/'
            date_time = ''
#             while self.go:
            while self.terminate_yet:
                data = c.recv(1024)  # Input argument from device
                data = data.decode('utf-8')
                data = data.strip()
                print(data)
                # When device sends "poweroff" initiate shutdown by setting go to false, removing all clients and closing all threads.
                if data == 'poweroff' or data == 'stopMeasure' or data[0:8] == 'date -s ':
#                     print("Shutdown starting")

                    if data == 'poweroff':
                        print("Shutdown starting")
                        print("shutdown_yet= " + str(self.shutdown_yet))
                        print('sv.list_of_variables_for_threads["shutdown_yet"] = ' + str(sv.list_of_variables_for_threads["shutdown_yet"]))  # for debug
                    elif data == 'date -s ':
                        os.system("sudo " + data)  # TODO
                        print("date and time synchronized")
                    elif  data == 'stopMeasure':
                        if c in self.run_measurement:
                            self.run_measurement.remove(c)
                            sv.list_of_variables_for_threads["run_measurement"] = self.run_measurement
                            print("Device removed")

                        self.is_measuring.pop(0)
                        sv.list_of_variables_for_threads["is_measuring"] = self.is_measuring

                        # CSVファイルクローズ処理
                        self.f_hr_csv.close()
                        self.f_rr_csv.close()
                        self.f_rtb_csv.close()
                        self.f_raw_csv.close()
                        self.f_sch_csv.close()
                        self.f_hea1_csv.close()  # for debug
                        self.f_hea2_csv.close()  # for debug
                        self.f_hea3_csv.close()  # for debug
                        self.f_hea4_csv.close()
                        self.f_hea5_csv.close()
                        self.f_hea6_csv.close()
                        self.f_hea7_csv.close()
                        self.f_hea8_csv.close()
                        self.f_hea9_csv.close()
                        self.f_hea10_csv.close()
                        self.f_hea11_csv.close()

                        print(filename_hr_csv + " is closed")
                        print(filename_rr_csv + " is closed")
                        print(filename_rtb_csv + " is closed")
                        print(filename_raw_csv + " is closed")
                        print(filename_sch_csv + " is closed")
                        print(filename_hea1_csv + " is closed")  # for debug
                        print(filename_hea2_csv + " is closed")  # for debug
                        print(filename_hea3_csv + " is closed")  # for debug
                        print(filename_hea4_csv + " is closed")
                        print(filename_hea5_csv + " is closed")
                        print(filename_hea6_csv + " is closed")
                        print(filename_hea7_csv + " is closed")
                        print(filename_hea8_csv + " is closed")
                        print(filename_hea9_csv + " is closed")
                        print(filename_hea10_csv + " is closed")
                        print(filename_hea11_csv + " is closed")

                        os.system("sudo chown futu-re:futu-re " + filepath + date_time + "/log*.csv")

                        # 計測終了時刻記録処理
                        timestamp = datetime.datetime.now()
                        date_time = timestamp.strftime('%Y%m%d_%H%M%S')
                        en_dt_tm = date_time.split('_')
                        self.f_rec_csv = open(filepath + self.filename_rec_csv, 'a')
                        if not self.f_rec_csv.closed:
                            self.f_rec_csv.write(en_dt_tm[0] + ' ' + en_dt_tm[1] + ' user' + str(self.user_serial_number) + ' end\n')
                        self.f_rec_csv.close()

                        self.measurement_start_time.clear()
                        sv.list_of_variables_for_threads["measurement_start_time"] = self.measurement_start_time

                    try:
                        #self.go = []
                        #self.list_of_variables_for_threads["go"] = self.go.pop(0)
                        #list_of_variables_for_threads["go"] = go.pop(0)
                        print('self.go = ' + str(self.go))  # for debug
#                         self.go.pop(0)

                        print('self.terminate_yet = ' + str(self.terminate_yet))  # for debug
                        self.terminate_yet.pop(0)
                        print('self.shutdown_yet = ' + str(self.shutdown_yet))  # for debug
                        if data == 'poweroff':
                            print('self.shutdown_yet = ' + str(self.shutdown_yet))  # for debug
                            self.shutdown_yet.pop(0)
                            print('self.shutdown_yet = ' + str(self.shutdown_yet))  # for debug

                        print("go= " + str(self.go))

                        sv.list_of_variables_for_threads["go"] = self.go
                        print("terminate_yet= " + str(self.terminate_yet))
                        sv.list_of_variables_for_threads["terminate_yet"] = self.terminate_yet
                        print("shutdown_yet= " + str(self.shutdown_yet))
                        sv.list_of_variables_for_threads["shutdown_yet"] = self.shutdown_yet
                        print('sv.list_of_variables_for_threads["shutdown_yet"] = ' + str(sv.list_of_variables_for_threads["shutdown_yet"]))  # for debug

                        for client in self.client_list:
                            print('try to remove client ' +
                                  str(self.address_list[self.client_list.index(client)]))
                            client.close()
                            print('remove client ' +
                                  str(self.address_list[self.client_list.index(client)]))
                        self.server.close()
                        print("server is now closed")
#                         os.system("echo 'power off\nquit' | bluetoothctl")  # TODO

                        if data == 'poweroff':
                            os.system("echo 'power off\nquit' | bluetoothctl")  # TODO

                    except Exception as error:
                        print("exception in for-loop in read_device: " + str(error))
#                 if not self.go:
                if not self.terminate_yet:

                    if data == 'poweroff':
                        print("Shutdown starting")

                    try:
                        #self.go = []
                        #self.list_of_variables_for_threads["go"] = self.go.pop(0)
                        #list_of_variables_for_threads["go"] = go.pop(0)
                        # self.go.pop(0)
                        print("go= " + str(self.go))

                        print("terminate_yet= " + str(self.terminate_yet))
                        print("shutdown_yet= " + str(self.shutdown_yet))

                        for client in self.client_list:
                            print('try to remove client ' +
                                  str(self.address_list[self.client_list.index(client)]))
                            client.close()
                            print('remove client ' +
                                  str(self.address_list[self.client_list.index(client)]))
                        self.server.close()
                        print("server is now closed")
#                         os.system("echo 'power off\nquit' | bluetoothctl")  # TODO

                        if data == 'poweroff':
                            os.system("echo 'power off\nquit' | bluetoothctl")  # TODO

                    except Exception as error:
                        print("exception in for-loop in read_device: " + str(error))

#                 elif data == 'startMeasure':
                elif data[0:12] == 'startMeasure':
                    self.run_measurement.append(c)
                    sv.list_of_variables_for_threads["run_measurement"] = self.run_measurement
                    print("Device added")

#                     data_splitted = data.split('_')[1]
#                     self.user_serial_number = data_splitted[1]

#                     self.user_serial_number = data.split('_')[1]

#                     data_splitted = data.split('_')
#                     print(data_splitted)  # for debug
#                     print(data_splitted[1])  # for debug
#                     self.user_serial_number = data_splitted[1]

                    self.user_serial_number = data[13:]

                    # CSVファイルオープン処理
                    # Get current time
                    timestamp = datetime.datetime.now()

                    date_time = timestamp.strftime('%Y%m%d_%H%M%S')
                    if not os.path.exists(filepath + date_time):
                        os.mkdir(filepath + date_time)
                    filename_hr_csv    = filepath + date_time + '/log_hr_'    + date_time + '.csv'  # CSV file for heart rate
                    filename_rr_csv    = filepath + date_time + '/log_rr_'    + date_time + '.csv'  # CSV file for respiration rate
                    filename_rtb_csv   = filepath + date_time + '/log_rtb_'   + date_time + '.csv'  # CSV file for real time breath
                    filename_raw_csv   = filepath + date_time + '/log_raw_'   + date_time + '.csv'  # CSV file for tracked data
                    filename_sch_csv   = filepath + date_time + '/log_sch_'   + date_time + '.csv'  # CSV file for schmittTrigger() internal data
                    filename_hea1_csv  = filepath + date_time + '/log_hea1_'  + date_time + '.csv'  # CSV file for heart_rate() internal data (fft_signal_out)  # for debug
                    filename_hea2_csv  = filepath + date_time + '/log_hea2_'  + date_time + '.csv'  # CSV file for heart_rate() internal data (fft_signal_out_dB)  # for debug
                    filename_hea3_csv  = filepath + date_time + '/log_hea3_'  + date_time + '.csv'  # CSV file for heart_rate() internal data (FFT_averaged)  # for debug
                    filename_hea4_csv  = filepath + date_time + '/log_hea4_'  + date_time + '.csv'  # CSV file for heart_rate() internal data (peak_freq)
                    filename_hea5_csv  = filepath + date_time + '/log_hea5_'  + date_time + '.csv'  # CSV file for heart_rate() internal data (peak_amplitude)
                    filename_hea6_csv  = filepath + date_time + '/log_hea6_'  + date_time + '.csv'  # CSV file for heart_rate() internal data (found_peak_index)
                    filename_hea7_csv  = filepath + date_time + '/log_hea7_'  + date_time + '.csv'  # CSV file for heart_rate() internal data (multiplication_factor)
                    filename_hea8_csv  = filepath + date_time + '/log_hea8_'  + date_time + '.csv'  # CSV file for heart_rate() internal data (peak_weighted)
                    filename_hea9_csv  = filepath + date_time + '/log_hea9_'  + date_time + '.csv'  # CSV file for heart_rate() internal data (close_peaks)
                    filename_hea10_csv = filepath + date_time + '/log_hea10_' + date_time + '.csv'  # CSV file for heart_rate() internal data (close_disturbing_peaks)
                    filename_hea11_csv = filepath + date_time + '/log_hea11_' + date_time + '.csv'  # CSV file for heart_rate () internal data (old_heart_freq_list)
                    filename_bp_csv    = filepath + date_time + '/log_bp_'    + date_time + '.csv'  # CSV file for blood pressure
                    filename_bpint_csv = filepath + date_time + '/log_bpint_' + date_time + '.csv'  # CSV file for blood_pressure() internal data

                    self.f_hr_csv    = open(filename_hr_csv,    'w')
                    self.f_rr_csv    = open(filename_rr_csv,    'w')
                    self.f_rtb_csv   = open(filename_rtb_csv,   'w')
                    self.f_raw_csv   = open(filename_raw_csv,   'w')
                    self.f_sch_csv   = open(filename_sch_csv,   'w')
                    self.f_hea1_csv  = open(filename_hea1_csv,  'w')  # for debug
                    self.f_hea2_csv  = open(filename_hea2_csv,  'w')  # for debug
                    self.f_hea3_csv  = open(filename_hea3_csv,  'w')  # for debug
                    self.f_hea4_csv  = open(filename_hea4_csv,  'w')
                    self.f_hea5_csv  = open(filename_hea5_csv,  'w')
                    self.f_hea6_csv  = open(filename_hea6_csv,  'w')
                    self.f_hea7_csv  = open(filename_hea7_csv,  'w')
                    self.f_hea8_csv  = open(filename_hea8_csv,  'w')
                    self.f_hea9_csv  = open(filename_hea9_csv,  'w')
                    self.f_hea10_csv = open(filename_hea10_csv, 'w')
                    self.f_hea11_csv = open(filename_hea11_csv, 'w')
                    self.f_bp_csv    = open(filename_bp_csv,    'w')
                    self.f_bpint_csv = open(filename_bpint_csv, 'w')

                    if not self.f_hr_csv.closed:
                        self.f_hr_csv.write('date time heart_rate reliability\n')
                    if not self.f_rr_csv.closed:
                        self.f_rr_csv.write('date time respiration_rate\n')
                    if not self.f_rtb_csv.closed:
                        self.f_rtb_csv.write('date time real_time_breath\n')
                    if not self.f_raw_csv.closed:
                        self.f_raw_csv.write('date time relative_distance bandpass_filtered_data_HR bandpass_filtered_data_HR_mvavg bandpass_filtered_data_RR\n')
                    if not self.f_sch_csv.closed:
                        self.f_sch_csv.write(
                                            'date time countHys trackedRRvector[countHys-1] Hcut Lcut ' +
                                            'freqArray[0] freqArray[1] freqArray[2] freqArray[3] freqArray[4] freqArray[5] freqArray[6] freqArray[7] ' +
                                            'FHighRR FLowRR respiratory_rate_data schNy schGa count\n'
                                            )
                    if not self.f_hea1_csv.closed:  # for debug
                        self.f_hea1_csv.write('date time fft_signal_out[0]\n')  # for debug
                    if not self.f_hea2_csv.closed:  # for debug
                        self.f_hea2_csv.write('date time fft_signal_out_dB[0]\n')  # for debug
                    if not self.f_hea3_csv.closed:  # for debug
                        self.f_hea3_csv.write('date time FFT_averaged[0]\n')  # for debug
                    if not self.f_hea4_csv.closed:
                        self.f_hea4_csv.write('date time peak_freq[0]\n')
                    if not self.f_hea5_csv.closed:
                        self.f_hea5_csv.write('date time peak_amplitude[0]\n')
                    if not self.f_hea6_csv.closed:
                        self.f_hea6_csv.write('date,time,' + \
                                                 'FFT_counter,index_in_FFT_old_values,' + \
                                                 'found_peak_index,found_heart_freq,found_heart_freq_amplitude_old,' + \
                                                 'next_largest_peak_amplitude,' + \
                                                 'found_heart_freq2,found_heart_rate\n')
                    if not self.f_hea7_csv.closed:
                        self.f_hea7_csv.write('date,time,multiplication_factor0\n')
                    if not self.f_hea8_csv.closed:
                        self.f_hea8_csv.write('date,time,peak_weighted[0]\n')
                    if not self.f_hea9_csv.closed:
                        self.f_hea9_csv.write('date,time,close_peaks[0]\n')
                    if not self.f_hea10_csv.closed:
                        self.f_hea10_csv.write('date,time,close_disturbing_peadks[0]\n')
                    if not self.f_hea11_csv.closed:
                        self.f_hea11_csv.write('date,time,old_heart_freq_list[0]\n')
                    if not self.f_bp_csv.closed:
                        self.f_bp_csv.write('date time SBP MBP DBP SBP_movavg MBP_movavg DBP_movavg\n')
                    if not self.f_bpint_csv.closed:
                        self.f_bpint_csv.write('date,time,movavgHRdata,idxpeak0,idxbottom,idxpea1,SBP,MBP,DBP\n')

                    sv.list_of_variables_for_threads["f_hr_csv"]    = self.f_hr_csv
                    sv.list_of_variables_for_threads["f_rr_csv"]    = self.f_rr_csv
                    sv.list_of_variables_for_threads["f_rtb_csv"]   = self.f_rtb_csv
                    sv.list_of_variables_for_threads["f_raw_csv"]   = self.f_raw_csv
                    sv.list_of_variables_for_threads["f_sch_csv"]   = self.f_sch_csv
                    sv.list_of_variables_for_threads["f_hea1_csv"]  = self.f_hea1_csv  # for debug
                    sv.list_of_variables_for_threads["f_hea2_csv"]  = self.f_hea2_csv  # for debug
                    sv.list_of_variables_for_threads["f_hea3_csv"]  = self.f_hea3_csv  # for debug
                    sv.list_of_variables_for_threads["f_hea4_csv"]  = self.f_hea4_csv
                    sv.list_of_variables_for_threads["f_hea5_csv"]  = self.f_hea5_csv
                    sv.list_of_variables_for_threads["f_hea6_csv"]  = self.f_hea6_csv
                    sv.list_of_variables_for_threads["f_hea7_csv"]  = self.f_hea7_csv
                    sv.list_of_variables_for_threads["f_hea8_csv"]  = self.f_hea8_csv
                    sv.list_of_variables_for_threads["f_hea9_csv"]  = self.f_hea9_csv
                    sv.list_of_variables_for_threads["f_hea10_csv"] = self.f_hea10_csv
                    sv.list_of_variables_for_threads["f_hea11_csv"] = self.f_hea11_csv
                    sv.list_of_variables_for_threads["f_bpint_csv"] = self.f_bpint_csv
                    sv.list_of_variables_for_threads["f_bp_csv"]    = self.f_bp_csv

                    # 計測開始時刻記録処理
                    st_dt_tm = date_time.split('_')
                    self.filename_rec_csv = 'log_rec_' + st_dt_tm[0] + '.csv'
                    if not os.path.exists(filepath + self.filename_rec_csv):
                        self.f_rec_csv = open(filepath + self.filename_rec_csv, 'w')
                        if not self.f_rec_csv.closed:
                            self.f_rec_csv.write('date time UserID start_or_end\n')
                    else:
                        self.f_rec_csv = open(filepath + self.filename_rec_csv, 'a')
                    if not self.f_rec_csv.closed:
#                         self.f_rec_csv.write(st_dt_tm[0] + ' ' + st_dt_tm[1] + ' user' + str(self.user_serial_number) + ' start\n')
                        self.f_rec_csv.write(st_dt_tm[0] + ' ' + st_dt_tm[1] + ' user' + self.user_serial_number + ' start\n')
                    self.f_rec_csv.close()

                    self.measurement_start_time.append(time.time())
                    sv.list_of_variables_for_threads["measurement_start_time"] = self.measurement_start_time

                    self.go = ["True"]
                    sv.list_of_variables_for_threads["go"] = self.go
                    self.is_measuring = ["True"]
                    sv.list_of_variables_for_threads["is_measuring"] = self.is_measuring

                    print("BluetoothServerModule: self.go = " + str(self.go))  # for debug

                elif data == 'write':
                    print("Bluetooth Write started")
                    self.initiate_write_heart_rate.append(0)
                    sv.list_of_variables_for_threads["initiate_write_heart_rate"] = self.initiate_write_heart_rate
                    self.start_write_to_csv_time = time.time()
                    sv.list_of_variables_for_threads["start_write_to_csv_time"] = self.start_write_to_csv_time

                    # self.initiate_write_heart_rate

        except Exception as error:
            print("last exception read_device: " + str(error))
            c.close()
            print('remove client: ' + str(self.address_list[self.client_list.index(c)]))
            if c in self.run_measurement:
                self.run_measurement.remove(c)
            self.client_list.remove(c)

    def write_data_to_app(self, data, data_type):
        # print(data + ' ' + data_type)

        dt_now = datetime.datetime.now()

        if data_type == 'heart rate':
            string = ' HR ' + str(data) + ' '
            # print(string)
            self.send_data(string)

            if not self.f_hr_csv.closed:
                self.f_hr_csv.write(str(dt_now) + ' ' + str(data) + '\n')

        elif data_type == 'breath rate':
            string = ' RR ' + str(data) + ' '
            # print(string)
            self.send_data(string)

            if not self.f_rr_csv.closed:
                self.f_rr_csv.write(str(dt_now) + ' ' + str(data) + '\n')

        elif data_type == 'real time breath':
            string = ' RTB ' + str(data) + ' '
            self.send_data(string)

            if not self.f_rtb_csv.closed:
                self.f_rtb_csv.write(str(dt_now) + ' ' + str(data) + '\n')

        elif data_type == 'blood pressure':
            data_ = data.split()
            data__ = data_[3] + ' ' + data_[4] + ' ' + data_[5]
            string = ' BP ' + str(data__) + ' '
            self.send_data(string)

            if not self.f_bp_csv.closed:
                self.f_bp_csv.write(str(dt_now) + ' ' + str(data) + '\n')

    def send_data(self, write):
        # print('Send data: ' + write)
        if self.is_measuring:
            for client in self.client_list:  # Send the same data to all clients connected
                try:
                    client.send(write.encode('utf-8'))      # write.encode('utf-8')
                except Exception as error:
                    print("Error send_data" + str(error))

    def add_data(self, i):  # TEMP: Make data somewhat random.
        data = [70 + math.sin(i), 20 + math.sin(i+math.pi/4)]
        noise = random.random()
        data[0] += 5*(noise - 0.5)
        noise = random.random()
        data[1] += noise
        data[0] = round(data[0])
        data[1] = round(data[1])
        return str(data[0]) + ' ' + str(data[1])

    # def get_data_from_queue(self):
    #     self.send_to_app_queue.put(self.add_data(1))
    #     return self.send_to_app_queue.get()

    # @staticmethod  # Test to send run variable to other threads, does not work yet.
    # def get_run(self):
    #    return self.run
