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
import pandas as pd


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
                        self.df_hr.to_csv(filepath + date_time + '/log_hr_' + date_time + '.csv', index=False)  # CSV file for heart rate
                        self.df_rr.to_csv(filepath + date_time + '/log_rr_' + date_time + '.csv', index=False)  # CSV file for respiration rate
                        self.df_rtb.to_csv(filepath + date_time + '/log_rtb_' + date_time + '.csv', index=False)  # CSV file for real time breath
                        self.df_raw.to_csv(filepath + date_time + '/log_raw_' + date_time + '.csv', index=False)  # CSV file for tracked data
                        self.df_sch.to_csv(filepath + date_time + '/log_sch_' + date_time + '.csv', index=False)  # CSV file for schmittTrigger() internal data
                        self.df_hea1.to_csv(filepath + date_time + '/log_hea1_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (fft_signal_out)  # for debug
                        self.df_hea2.to_csv(filepath + date_time + '/log_hea2_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (fft_signal_out_dB)  # for debug
                        self.df_hea3.to_csv(filepath + date_time + '/log_hea3_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (FFT_averaged)  # for debug
                        self.df_hea4.to_csv(filepath + date_time + '/log_hea4_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (peak_freq)
                        self.df_hea5.to_csv(filepath + date_time + '/log_hea5_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (peak_amplitude)
                        self.df_hea6.to_csv(filepath + date_time + '/log_hea6_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (found_peak_index)
                        self.df_hea7.to_csv(filepath + date_time + '/log_hea7_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (multiplication_factor)
                        self.df_hea8.to_csv(filepath + date_time + '/log_hea8_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (peak_weighted)
                        self.df_hea9.to_csv(filepath + date_time + '/log_hea9_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (close_peaks)
                        self.df_hea10.to_csv(filepath + date_time + '/log_hea10_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (close_disturbing_peaks)
                        self.df_hea11.to_csv(filepath + date_time + '/log_hea11_' + date_time + '.csv', index=False)  # CSV file for heart_rate() internal data (old_heart_freq_list)  # for debug
                        self.df_bp.to_csv(filepath + date_time + '/log_bp_' + date_time + '.csv', index=False)  # CSV file for blood pressure
                        self.df_bpint.to_csv(filepath + date_time + '/log_bpint_' + date_time + '.csv', index=False)  # CSV file for blood_pressure() internal data
                        self.f_daq_run_prctim_csv.close()
#                         self.df_daq_run_prctim.to_csv(filepath + date_time + '/log_daq_run_prctim_' + date_time + '.csv', index=False)  # CSV file for recording processing time of run()@data_acquisition_module.py
                        self.f_sgp_hre_prctim_csv.close()
#                         self.df_sgp_hre_prctim.to_csv(filepath + date_time + '/log_sgp_hre_prctim_' + date_time + '.csv', index=False)  # CSV file for recording processing time of heart_rate()@signal_processing_module.py
                        self.f_sgp_rre_prctim_csv.close()
#                         self.df_sgp_rre_prctim.to_csv(filepath + date_time + '/log_sgp_rre_prctim_' + date_time + '.csv', index=False)  # CSV file for recording processing time of schmittTrigger()@signal_processing_module.py
                        self.f_sgp_bpe_prctim_csv.close()
#                         self.df_sgp_bpe_prctim.to_csv(filepath + date_time + '/log_sgp_bpe_prctim_' + date_time + '.csv', index=False)  # CSV file for recording processing time of blood_pressure()@signal_processing_module.py
                        self.f_info_csv.close()
#                         self.df_info.to_csv(filepath + date_time + '/log_info_' + date_time + '.csv', index=False)  # CSV file for recording "info" variable value of get_data()@data_acquisition_module.py

                        print(filename_daq_run_prctim_csv + " is closed")
                        print(filename_sgp_hre_prctim_csv + " is closed")
                        print(filename_sgp_rre_prctim_csv + " is closed")
                        print(filename_sgp_bpe_prctim_csv + " is closed")
                        print(filename_info_csv + " is closed")

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

                    # データフレーム作成処理
                    # Get current time
                    timestamp = datetime.datetime.now()

                    date_time = timestamp.strftime('%Y%m%d_%H%M%S')
                    if not os.path.exists(filepath + date_time):
                        os.mkdir(filepath + date_time)
                    filename_daq_run_prctim_csv = filepath + date_time + '/log_daq_run_prctim_' + date_time + '.csv'  # CSV file for recording processing time of run()@data_acquisition_module.py
                    filename_sgp_hre_prctim_csv = filepath + date_time + '/log_sgp_hre_prctim_' + date_time + '.csv'  # CSV file for recording processing time of heart_rate()@signal_processing_module.py
                    filename_sgp_rre_prctim_csv = filepath + date_time + '/log_sgp_rre_prctim_' + date_time + '.csv'  # CSV file for recording processing time of schmittTrigger()@signal_processing_module.py
                    filename_sgp_bpe_prctim_csv = filepath + date_time + '/log_sgp_bpe_prctim_' + date_time + '.csv'  # CSV file for recording processing time of blood_pressure()@signal_processing_module.py
                    filename_info_csv = filepath + date_time + '/log_info_' + date_time + '.csv'  # CSV file for recording "info" variable value of get_data()@data_acquisition_module.py

                    self.df_hr = pd.DataFrame(columns=["date", "time", "heart_rate", "reliability"])
                    self.df_rr = pd.DataFrame(columns=["date", "time", "respiration_rate"])
                    self.df_rtb = pd.DataFrame(columns=["date", "time", "real_time_breath"])
                    self.df_raw = pd.DataFrame(columns=["date", "time", "relative_distance", "bandpass_filtered_data_HR", "bandpass_filtered_data_HR_mvavg", "bandpass_filtered_data_RR"])
                    self.df_sch = pd.DataFrame(columns=["date", "time", "countHys", "trackedRRvector[countHys-1]", "Hcut", "Lcut", \
                                                        "freqArray[0]", "freqArray[1]", "freqArray[2]", "freqArray[3]", "freqArray[4]", "freqArray[5]", "freqArray[6]", "freqArray[7]", \
                                                        "FHighRR", "FLowRR", "respiratory_rate_data", "schNy", "schGa", "count"])
                    columns_lst_for_hea1 = ["date", "time"]
                    freq_range_div_num = sv.list_of_variables_for_threads["freq_range_div_num"]
                    for i in range(freq_range_div_num):
                        columns_lst_for_hea1.append("fft_signal_out[" + str(i) + "]")
                    self.df_hea1 = pd.DataFrame(columns=columns_lst_for_hea1)
                    columns_lst_for_hea2 = ["date", "time"]
                    for i in range(freq_range_div_num):
                        columns_lst_for_hea2.append("fft_signal_out_dB[" + str(i) + "]")
                    self.df_hea2 = pd.DataFrame(columns=columns_lst_for_hea2)
                    columns_lst_for_hea3 = ["date", "time"]
                    for i in range(freq_range_div_num):
                        columns_lst_for_hea3.append("FFT_averaged[" + str(i) + "]")
                    self.df_hea3 = pd.DataFrame(columns=columns_lst_for_hea3)
                    self.df_hea4 = pd.DataFrame(columns=["date", "time"])
                    self.df_hea5 = pd.DataFrame(columns=["date", "time"])
                    self.df_hea6 = pd.DataFrame(columns=["date", "time", "FFT_counter", "index_in_FFT_old_values", "found_peak_index", \
                                                         "found_heart_freq", "found_heart_freq_amplitude_old", "next_largest_peak_amplitude", \
                                                         "found_heart_freq2", "found_heart_rate"])
                    self.df_hea7 = pd.DataFrame(columns=["date", "time"])
                    self.df_hea8 = pd.DataFrame(columns=["date", "time"])
                    self.df_hea9 = pd.DataFrame(columns=["date", "time"])
                    self.df_hea10 = pd.DataFrame(columns=["date", "time"])
                    columns_lst_for_hea11 = ["date", "time"]
                    upl_of_old_heart_freq_list = sv.list_of_variables_for_threads["upl_of_old_heart_freq_list"]
                    for i in range(upl_of_old_heart_freq_list):
                        columns_lst_for_hea11.append("old_heart_freq_list[" + str(i) + "]")
                    self.df_hea11 = pd.DataFrame(columns=columns_lst_for_hea11)
                    self.df_bp = pd.DataFrame(columns=["date", "time", "SBP", "MBP", "DBP", "SBP_movavg", "MBP_movavg", "DBP_movavg"])
                    self.df_bpint = pd.DataFrame(columns=["date", "time", "movavgHRdata", "idxpeak0", "idxbottom", "idxpea1", "SBP", "MBP", "DBP"])
                    self.f_daq_run_prctim_csv = open(filename_daq_run_prctim_csv, 'w')
#                     self.df_daq_run_prctim = pd.DataFrame(columns=["date", "time", "processing_time[ms]", "remark"])
                    self.f_sgp_hre_prctim_csv = open(filename_sgp_hre_prctim_csv, 'w')
#                     self.df_sgp_hre_prctim = pd.DataFrame(columns=["date", "time", "processing_time[ms]", "remark"])
                    self.f_sgp_rre_prctim_csv = open(filename_sgp_rre_prctim_csv, 'w')
#                     self.df_sgp_rre_prctim = pd.DataFrame(columns=["date", "time", "processing_time[ms]", "remark"])
                    self.f_sgp_bpe_prctim_csv = open(filename_sgp_bpe_prctim_csv, 'w')
#                     self.df_sgp_bpe_prctim = pd.DataFrame(columns=["date", "time", "processing_time[ms]", "remark"])
                    self.f_info_csv = open(filename_info_csv, 'w')
#                     self.df_info = pd.DataFrame(columns=["date", "time", "tick", "data_saturated", "missed_data", "data_quality_warning"])

                    if not self.f_daq_run_prctim_csv.closed:
                        self.f_daq_run_prctim_csv.write('date time processing_time[ms] remark\n')
                    if not self.f_sgp_hre_prctim_csv.closed:
                        self.f_sgp_hre_prctim_csv.write('date time processing_time[ms] remark\n')
                    if not self.f_sgp_rre_prctim_csv.closed:
                        self.f_sgp_rre_prctim_csv.write('date time processing_time[ms] remark\n')
                    if not self.f_sgp_bpe_prctim_csv.closed:
                        self.f_sgp_bpe_prctim_csv.write('date time processing_time[ms] remark\n')
                    if not self.f_info_csv.closed:
                        self.f_info_csv.write('date time tick data_saturated missed_data data_quality_warning\n')

                    sv.list_of_variables_for_threads["f_daq_run_prctim_csv"] = self.f_daq_run_prctim_csv
                    sv.list_of_variables_for_threads["f_sgp_hre_prctim_csv"] = self.f_sgp_hre_prctim_csv
                    sv.list_of_variables_for_threads["f_sgp_rre_prctim_csv"] = self.f_sgp_rre_prctim_csv
                    sv.list_of_variables_for_threads["f_sgp_bpe_prctim_csv"] = self.f_sgp_bpe_prctim_csv
                    sv.list_of_variables_for_threads["f_info_csv"] = self.f_info_csv

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

        dt_now = sv.list_of_variables_for_threads["current_date_time"]

        if data_type == 'heart rate':
            string = ' HR ' + str(data) + ' '
            # print(string)
            self.send_data(string)

#             if not self.f_hr_csv.closed:
#                 self.f_hr_csv.write(str(dt_now) + ' ' + str(data) + '\n')
            dt_now_lst = str(dt_now).split()
            data_lst = data.split()
            new_data = {
                "date": [dt_now_lst[0]],
                "time": [dt_now_lst[1]],
                "heart_rate": [data_lst[0]],
                "reliability": [data_lst[1]]
            }
            new_data_df = pd.DataFrame(new_data)
            self.df_hr = pd.concat([self.df_hr, new_data_df], axis=0, ignore_index=True)

        elif data_type == 'breath rate':
            string = ' RR ' + str(data) + ' '
            # print(string)
            self.send_data(string)

#             if not self.f_rr_csv.closed:
#                 self.f_rr_csv.write(str(dt_now) + ' ' + str(data) + '\n')
            dt_now_lst = str(dt_now).split()
            new_data = {
                "date": [dt_now_lst[0]],
                "time": [dt_now_lst[1]],
                "respiration_rate": [data]
            }
            new_data_df = pd.DataFrame(new_data)
            self.df_rr = pd.concat([self.df_rr, new_data_df], axis=0, ignore_index=True)

        elif data_type == 'real time breath':
            string = ' RTB ' + str(data) + ' '
            self.send_data(string)

#             if not self.f_rtb_csv.closed:
#                 self.f_rtb_csv.write(str(dt_now) + ' ' + str(data) + '\n')
            dt_now_lst = str(dt_now).split()
            new_data = {
                "date": [dt_now_lst[0]],
                "time": [dt_now_lst[1]],
                "real_time_breath": [data]
            }
            new_data_df = pd.DataFrame(new_data)
            self.df_rtb = pd.concat([self.df_rtb, new_data_df], axis=0, ignore_index=True)

        elif data_type == 'blood pressure':
            data_ = data.split()
            data__ = data_[3] + ' ' + data_[4] + ' ' + data_[5]
            string = ' BP ' + str(data__) + ' '
            self.send_data(string)

#             if not self.f_bp_csv.closed:
#                 self.f_bp_csv.write(str(dt_now) + ' ' + str(data) + '\n')
            dt_now_lst = str(dt_now).split()
            new_data = {
                "date": [dt_now_lst[0]],
                "time": [dt_now_lst[1]],
                "SBP": [data_[0]],
                "MBP": [data_[1]],
                "DBP": [data_[2]],
                "SBP_movavg": [data_[3]],
                "MBP_movavg": [data_[4]],
                "DBP_movavg": [data_[5]]
            }
            new_data_df = pd.DataFrame(new_data)
            self.df_bp = pd.concat([self.df_bp, new_data_df], axis=0, ignore_index=True)

    def write_data_only_to_storage(self, data_to_write, data_type):
        dt_now = sv.list_of_variables_for_threads["current_date_time"]
        dt_now_lst = str(dt_now).split()

        if data_type == 'raw':
            data_lst = data_to_write.split()
            new_data = {
                "date": [dt_now_lst[0]],
                "time": [dt_now_lst[1]],
                "relative_distance": [data_lst[0]],
                "bandpass_filtered_data_HR": [data_lst[1]],
                "bandpass_filtered_data_HR_mvavg": [data_lst[2]],
                "bandpass_filtered_data_RR": [data_lst[3]]
            }
            new_data_df = pd.DataFrame(new_data)
            self.df_raw = pd.concat([self.df_raw, new_data_df], axis=0, ignore_index=True)

        elif data_type == 'bpint':
            data_lst = data_to_write.split(',')
            new_data = {
                "date": [dt_now_lst[0]],
                "time": [dt_now_lst[1]],
                "movavgHRdata": [data_lst[0]],
                "idxpeak0": [data_lst[1]],
                "idxbottom": [data_lst[2]],
                "idxpea1": [data_lst[3]],
                "SBP": [data_lst[4]],
                "MBP": [data_lst[5]],
                "DBP": [data_lst[6]]
            }
            new_data_df = pd.DataFrame(new_data)
            self.df_bpint = pd.concat([self.df_bpint, new_data_df], axis=0, ignore_index=True)

#         elif data_type == 'daq_run_prctim' or data_type == 'sgp_hre_prctim' or data_type == 'sbp_rre_prctim' or data_type == 'sgp_bpe_prctim':
#             data_lst = data_to_write.split()
#             new_data = {
#                 "date": [data_lst[0]],
#                 "time": [data_lst[1]],
#                 "processing_time[ms]": [data_lst[2]],
#                 "remark": [data_lst[3]]
#             }
#             new_data_df = pd.DataFrame(new_data)
#             if data_type == 'daq_run_prctim':
#                 self.df_daq_run_prctim = pd.concat([self.df_daq_run_prctim, new_data_df], axis=0, ignore_index=True)
#             elif data_type == 'sgp_hre_prctim':
#                 self.df_sgp_hre_prctim = pd.concat([self.df_sgp_hre_prctim, new_data_df], axis=0, ignore_index=True)
#             elif data_type == 'sgp_rre_prctim':
#                 self.df_sgp_rre_prctim = pd.concat([self.df_sgp_rre_prctim, new_data_df], axis=0, ignore_index=True)
#             elif data_type == 'sgp_bpe_prctim':
#                 self.df_sgp_bpe_prctim = pd.concat([self.df_sgp_bpe_prctim, new_data_df], axis=0, ignore_index=True)

#         elif data_type == 'info':
#             data_lst = data_to_write.split()
#             new_data = {
#                 "date": [dt_now_lst[0]],
#                 "time": [dt_now_lst[1]],
#                 "tick": [data_lst[0]],
#                 "data_saturated": [data_lst[1]],
#                 "missed_data": [data_lst[2]],
#                 "data_quality_warning": [data_lst[3]]
#             }
#             new_data_df = pd.DataFrame(new_data)
#             self.df_info = pd.concat([self.df_info, new_data_df], axis=0, ignore_index=True)

        elif data_type == 'hea6':
            data_lst = data_to_write.split(',')
            new_data = {
                "date": [dt_now_lst[0]],
                "time": [dt_now_lst[1]],
                "FFT_counter": [data_lst[0]],
                "index_in_FFT_old_values": [data_lst[1]],
                "found_peak_index": [data_lst[2]],
                "found_heart_freq": [data_lst[3]],
                "found_heart_freq_amplitude_old": [data_lst[4]],
                "next_largest_peak_amplitude": [data_lst[5]],
                "found_heart_freq2": [data_lst[6]],
                "found_heart_rate": [data_lst[7]]
            }
            new_data_df = pd.DataFrame(new_data)
            self.df_hea6 = pd.concat([self.df_hea6, new_data_df], axis=0, ignore_index=True)

        elif data_type[0:3] == 'hea':
            new_data = {
                "date": [dt_now_lst[0]],
                "time": [dt_now_lst[1]]
            }

            if data_type == 'hea1' or data_type == 'hea2' or data_type == 'hea3':
                loop_cnt_limit = sv.list_of_variables_for_threads["freq_range_div_num"]
            else:
                loop_cnt_limit = len(data_to_write)

            for i in range(loop_cnt_limit):
                if data_type == 'hea1':
                    key_name = "fft_signal_out[" + str(i) + "]"
                elif data_type == 'hea2':
                    key_name = "fft_signal_out_dB[" + str(i) + "]"
                elif data_type == 'hea3':
                    key_name = "FFT_averaged[" + str(i) + "]"
                elif data_type == 'hea4':
                    key_name = "peak_freq[" + str(i) + "]"
                elif data_type == 'hea5':
                    key_name = "peak_amplitude[" + str(i) + "]"
                elif data_type == 'hea7':
                    key_name = "multiplication_factor" + str(i)
                elif data_type == 'hea8':
                    key_name = "peak_weighted[" + str(i) + "]"
                elif data_type == 'hea9':
                    key_name = "close_peaks[" + str(i) + "]"
                elif data_type == 'hea10':
                    key_name = "close_disturbing_peaks[" + str(i) + "]"
                elif data_type == 'hea11':
                    key_name = "old_heart_freq_list[" + str(i) + "]"
                new_data[key_name] = [data_to_write[i]]

            new_data_df = pd.DataFrame(new_data)
            if data_type == 'hea1':
                self.df_hea1 = pd.concat([self.df_hea1, new_data_df], axis=0, ignore_index=True)
            elif data_type == 'hea2':
                self.df_hea2 = pd.concat([self.df_hea2, new_data_df], axis=0, ignore_index=True)
            elif data_type == 'hea3':
                self.df_hea3 = pd.concat([self.df_hea3, new_data_df], axis=0, ignore_index=True)
            elif data_type == 'hea4':
                self.df_hea4 = pd.concat([self.df_hea4, new_data_df], axis=0, ignore_index=True)
            elif data_type == 'hea5':
                self.df_hea5 = pd.concat([self.df_hea5, new_data_df], axis=0, ignore_index=True)
            elif data_type == 'hea7':
                self.df_hea7 = pd.concat([self.df_hea7, new_data_df], axis=0, ignore_index=True)
            elif data_type == 'hea8':
                self.df_hea8 = pd.concat([self.df_hea8, new_data_df], axis=0, ignore_index=True)
            elif data_type == 'hea9':
                self.df_hea9 = pd.concat([self.df_hea9, new_data_df], axis=0, ignore_index=True)
            elif data_type == 'hea10':
                self.df_hea10 = pd.concat([self.df_hea10, new_data_df], axis=0, ignore_index=True)
            elif data_type == 'hea11':
                self.df_hea11 = pd.concat([self.df_hea11, new_data_df], axis=0, ignore_index=True)

        elif data_type == 'sch':
            data_lst = data_to_write.split()
            new_data = {
                "date": [dt_now_lst[0]],
                "time": [dt_now_lst[1]],
                "countHys": [data_lst[0]],
                "trackedRRvector[countHys-1]": [data_lst[1]],
                "Hcut": [data_lst[2]],
                "Lcut": [data_lst[3]],
                "FHighRR": [data_lst[12]],
                "FLowRR": [data_lst[13]],
                "respiratory_rate_data": [data_lst[14]],
                "schNy": [data_lst[15]],
                "schGa": [data_lst[16]],
                "count": [data_lst[17]]
            }

            for i in range(8):
                key_name = "freqArray[" + str(i) + "]"
                new_data[key_name] = [data_lst[i + 4]]

            new_data_df = pd.DataFrame(new_data)
            self.df_sch = pd.concat([self.df_sch, new_data_df], axis=0, ignore_index=True)

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
