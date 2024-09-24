import numpy as np
from scipy import signal  # Det här kanske behöver importeras på något annat sätt.
import matplotlib.pyplot as plt  # TODO: ta bort sen
import time  # TODO: Ta bort sen
from scipy.fftpack import fft
from scipy.signal import spectrogram  # To plot spectrogram of FFT.
import threading
import queue
import os

import datetime
from decimal import Decimal, ROUND_HALF_UP

import filter
import shared_variables as sv
# import asyncio

class SignalProcessing:

    # FFTfreq and FFTamplitude are temporary for testing FFT. Remove later
#     def __init__(self, list_of_variables_for_threads, bluetooth_server, FFTfreq, FFTamplitude):
    def __init__(self, bluetooth_server, FFTfreq, FFTamplitude):
        self.list_of_variables_for_threads =  sv.list_of_variables_for_threads

#         self.shutdown_yet =  list_of_variables_for_threads["shutdown_yet"]
#         self.go =  list_of_variables_for_threads["go"]
        self.HR_filtered_queue =  sv.list_of_variables_for_threads["HR_filtered_queue"]
        self.HR_final_queue =  sv.list_of_variables_for_threads["HR_final_queue"]       # TODO ta bort
        self.sample_freq =  sv.list_of_variables_for_threads["sample_freq"]
        self.bluetooth_server = bluetooth_server

        # Variables for Schmitt Trigger
        self.RR_filtered_queue =  sv.list_of_variables_for_threads["RR_filtered_queue"]
        self.RR_final_queue =  sv.list_of_variables_for_threads["RR_final_queue"]
        self.freqArrayTemp_last = []  # If no breathing rate is found use last value
        # print(list(self.RR_final_queue.queue))
        self.RTB_final_queue =  sv.list_of_variables_for_threads["RTB_final_queue"]
        self.time_when_sent_last_value = None  # to check time passed after sent a value

        # Variables for Blodd Pressure
        self.HR_filtered_queue_movavg =  sv.list_of_variables_for_threads["HR_filtered_queue_movavg"]

        # Variables for Pulse detection
        self.index_fft = 0
#         self.T_resolution = 20  # förut 30
        self.T_resolution = 40  # förut 30
        self.overlap = 90  # Percentage of old values for the new FFT
        self.beta = 1  # Kaiser window form
        self.tau = 12  # TODO Beskriva alla variabler
        # Data in vector with length of window
#         self.fft_window = np.zeros(self.T_resolution*self.sample_freq)  # Width in samples of FFT
        self.fft_window = np.zeros(self.T_resolution * int(self.sample_freq))  # Width in samples of FFT
        self.window_width = int(len(self.fft_window))
        self.total_fft_length = int(1.5*self.window_width)
        # window_width_half = int(window_width/2)  # Since FFT only processes half of freq (Nyqvist)
        self.window_slide = int(np.round(self.window_width*(1-self.overlap/100)))
        self.window_slide_global =  sv.list_of_variables_for_threads["window_slide"]
        self.window_slide_global = self.window_slide
        # self.freq = self.sample_freq * \
        #    np.arange(self.total_fft_length/2)/self.window_width  # Evenly spaced freq array
#         self.freq = np.linspace(0, self.sample_freq/2, num=self.total_fft_length/2)
        self.freq = np.linspace(0, self.sample_freq/2, num=int(self.total_fft_length/2))
        self.delta_T = self.window_slide / self.sample_freq
        # int(round(self.tau / self.delta_T))  # Make tau is larger than delta_T, else it will be zero and programme will fail.
        self.number_of_old_FFT = 15
        self.FFT_old_values = np.zeros((self.number_of_old_FFT, int(
            self.total_fft_length/2)))  # Saving old values for moving mean
        sv.list_of_variables_for_threads["freq_range_div_num"] = int(self.total_fft_length/2)

        self.F_scan_lower = 0.8
        self.F_scan_upper = 3
        self.idx_lst_for_hea3 = []
        freq = np.linspace(0, self.sample_freq/2, num=int(self.total_fft_length/2))
        for i, itm in enumerate(freq):
            if itm > self.F_scan_lower and itm <= self.F_scan_upper:
                self.idx_lst_for_hea3.append(i)
        self.peak_freq_linspace = np.linspace(self.F_scan_lower, self.F_scan_upper, num=len(self.idx_lst_for_hea3))
        sv.list_of_variables_for_threads["idx_lst_for_hea3"] = self.idx_lst_for_hea3
        sv.list_of_variables_for_threads["freq"] = freq
        sv.list_of_variables_for_threads["peak_freq_linspace"] = self.peak_freq_linspace

        self.upl_of_old_heart_freq_list = 20  # upper limit of number of elements in old_heart_freq_list
        sv.list_of_variables_for_threads["upl_of_old_heart_freq_list"] = self.upl_of_old_heart_freq_list

        self.measurement_start_time =  sv.list_of_variables_for_threads["measurement_start_time"]

        # Starta heart_rate
        print("Start thread heart_rate")
        self.heart_rate_thread = threading.Thread(target=self.heart_rate)
        self.heart_rate_thread.start()

        self.window_size_for_bp_movavg = 13
        self.f_sgp_hre_prctim_csv =  sv.list_of_variables_for_threads["f_sgp_hre_prctim_csv"]
        self.movavg_SBP = filter.Filter('movavg', window_size_for_movavg=self.window_size_for_bp_movavg)
        self.movavg_MBP = filter.Filter('movavg', window_size_for_movavg=self.window_size_for_bp_movavg)
        self.movavg_DBP = filter.Filter('movavg', window_size_for_movavg=self.window_size_for_bp_movavg)

        # Starta blood_pressure
        print("Start thread blood_pressure")
        self.f_sgp_bpe_prctim_csv =  sv.list_of_variables_for_threads["f_sgp_bpe_prctim_csv"]
        self.blood_pressure_thread = threading.Thread(target=self.blood_pressure)
        self.blood_pressure_thread.start()

        self.f_sgp_rre_prctim_csv =  sv.list_of_variables_for_threads["f_sgp_rre_prctim_csv"]

        # Starta schmitt
        print("Start thread schmittTrigger")
        self.schmittTrigger_thread = threading.Thread(target=self.schmittTrigger)
        self.schmittTrigger_thread.start()

        self.last_time = time.time()
        self.time = time.time()

        # Temporary for test of FFT and saving to csv
        self.FFTfreq = FFTfreq
        self.FFTamplitude = FFTamplitude
        self.peak_freq = []
        self.peak_amplitude = []
        self.peak_weighted = []
        self.len_fft = 0
        self.heart_rate_csv =  sv.list_of_variables_for_threads["heart_rate_csv"]
        self.start_write_to_csv_time =  sv.list_of_variables_for_threads["start_write_to_csv_time"]
        self.initiate_write_heart_rate =  sv.list_of_variables_for_threads["initiate_write_heart_rate"]
        self.heart_rate_reliability_csv = []
        self.heart_rate_spectrum = []
        self.heart_rate_frequency = []

    # Kaos i koden, behöver struktureras upp och alla konstanter måste defineras i början
    # Följer just nu Matlab strukturen.

    def heart_rate(self):  # MAIN for finding pulse
        while sv.list_of_variables_for_threads["terminate_yet"]:

            if sv.list_of_variables_for_threads["is_measuring"]:

                # print("heart_rate thread started")
                index_in_FFT_old_values = 0  # Placement of old FFT in FFT_old_values
                FFT_counter = 1  # In start to avg over FFT_counter before FFT_old_values is filled to max
                found_heart_freq_old = 180/60  # Guess the first freq

                found_heart_freq_amplitude_old = -40  # The initial value is assumed to be -40dB to avoid referencing before assignment.

                # Variables for weigthed peaks
                #multiplication_factor = 20
                time_constant = 2
#                 start_time = time.time()
                first_real_value = True  # the first real heart rate found
                old_heart_freq_list = []  # old values

                found_peak_reliability = "None"
                found_peak_reliability_int = 0
                # A variable that indicates when the measurement data is stable
                measurement_data_stable_state = False

#                 while self.go:
                while sv.list_of_variables_for_threads["is_measuring"]:

                    self.measurement_start_time =  sv.list_of_variables_for_threads["measurement_start_time"]

                    if not self.measurement_start_time:
                        continue
                    else:
                        start_time = self.measurement_start_time[0]

                    data_to_write_in_hea6 = ""

                    dt_stlp = datetime.datetime.now()

                    # print("in while loop heart_rate")
                    fft_signal_out = self.windowedFFT()

#                     self.bluetooth_server.write_data_only_to_storage(fft_signal_out, 'hea1')

                    dt_tmp = sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_hre_prctim_csv"], dt_stlp, "calculate_fft_signal_out")
#                     dt_tmp = sv.clc_elpsd_tim(self.bluetooth_server, "sgp_hre_prctim", dt_stlp, "calculate_fft_signal_out")

                    fft_signal_out_dB = 20*np.log10(fft_signal_out)  # As of May 7, lenght of vector is 600

#                     self.bluetooth_server.write_data_only_to_storage(fft_signal_out_dB, 'hea2')

                    dt_tmp = sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_hre_prctim_csv"], dt_tmp, "calculate_fft_signal_out_dB")
#                     dt_tmp = sv.clc_elpsd_tim(self.bluetooth_server, "sgp_hre_prctim", dt_tmp, "calculate_fft_signal_out_dB")

                    self.FFT_old_values[index_in_FFT_old_values][:] = fft_signal_out_dB

                    # saved_old = self.FFT_old_values[:, 2] #to print
                    # fft movemean
                    FFT_averaged = self.mean_of_old_values(FFT_counter)

                    self.bluetooth_server.write_data_only_to_storage(FFT_averaged[self.idx_lst_for_hea3[0]:self.idx_lst_for_hea3[-1]+1], 'hea3')
#                     asyncio.run(self.bluetooth_server.write_data_only_to_storage(FFT_averaged[self.idx_lst_for_hea3[0]:self.idx_lst_for_hea3[-1]+1], 'hea3'))

                    dt_tmp = sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_hre_prctim_csv"], dt_tmp, "calculate_FFT_averaged")
#                     dt_tmp = sv.clc_elpsd_tim(self.bluetooth_server, "sgp_hre_prctim", dt_tmp, "calculate_FFT_averaged")

                    #print("Length of averaged FFT: ", len(FFT_averaged))
                    # Returns the peaks in set inteval from averaged FFT
                    peak_freq, peak_amplitude = self.findPeaks(FFT_averaged)

#                     self.bluetooth_server.write_data_only_to_storage(peak_freq, 'hea4')

#                     self.bluetooth_server.write_data_only_to_storage(peak_amplitude, 'hea5')

                    data_to_write_in_hea6 += str(FFT_counter) + "," + \
                                             str(index_in_FFT_old_values) + ","

                    dt_tmp = sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_hre_prctim_csv"], dt_tmp, "calculate_peak_f_a")
#                     dt_tmp = sv.clc_elpsd_tim(self.bluetooth_server, "sgp_hre_prctim", dt_tmp, "calculate_peak_f_a")

#                     if len(peak_freq) > 0 and np.amin(peak_amplitude) > -40 and np.amax(peak_amplitude) > -30 and time.time() - start_time > 50:
                    if len(peak_freq) > 0 and np.amin(peak_amplitude) > -45 and np.amax(peak_amplitude) > -35 and time.time() - start_time > 50:
#                         if not measurement_data_stable_state:
#                             measurement_data_stable_state = True
                        # In case zero peaks, use last value, and to not trigger on noise, and there is just noise before 30 seconds has passed
                        # Going into own method when tested and working staying in "main loop"
                        delta_freq = []
                        for freq in peak_freq:
                            delta_freq.append(freq - found_heart_freq_old)
                        self.peak_weighted = []
                        close_peaks = []
                        close_disturbing_peaks = []
                        try:

                            multiplication_factor_lst = []

                            for i in range(0, len(peak_freq)):  # Weight the peaks found depending on their amplitude,
                                if peak_freq[i] < 0.9:
                                    multiplication_factor = 5  # to lower the noise peak under 0.9 Hz
                                elif peak_freq[i] < 1:
                                    multiplication_factor = 7  # to lower the noise peak under 1 Hz
                                else:
                                    multiplication_factor = 10

                                multiplication_factor_lst.append(multiplication_factor)

                                # distance to the last tracked peak, and on the frequency (the noise is kind of 1/f, so to to fix that multiply with f)
                                self.peak_weighted.append(peak_amplitude[i] + multiplication_factor * np.exp(
                                    -np.abs(peak_freq[i] - found_heart_freq_old) / time_constant) * np.sqrt(
                                    np.sqrt(peak_freq[i])))
                                if np.abs(peak_freq[i] - found_heart_freq_old) < 0.2 and np.abs(
                                        peak_amplitude[i] - found_heart_freq_amplitude_old) < 4 and (
                                        found_heart_freq_old < 1 or peak_freq[i] > 1):
                                    # To average peaks if they are close
                                    close_peaks.append(peak_freq[i])
                                elif np.abs(peak_freq[i] - found_heart_freq_old) < 0.5 and np.abs(
                                        peak_amplitude[i] - found_heart_freq_amplitude_old) < 5:
#                                 elif np.abs(peak_freq[i] - found_heart_freq_old) < 0.5 and np.abs(peak_freq[i] - found_heart_freq_old) >= 0.4 \
#                                      and np.abs(peak_amplitude[i] - found_heart_freq_amplitude_old) < 5 and np.abs(peak_amplitude[i] - found_heart_freq_amplitude_old) >= 4:
                                    # If there is a lot of peaks to disturb the measurement
                                    close_disturbing_peaks.append(peak_freq[i])

#                             self.bluetooth_server.write_data_only_to_storage(multiplication_factor_lst, 'hea7')

#                             self.bluetooth_server.write_data_only_to_storage(self.peak_weighted, 'hea8')

                            self.bluetooth_server.write_data_only_to_storage(close_peaks, 'hea9')
#                             asyncio.run(self.bluetooth_server.write_data_only_to_storage(close_peaks, 'hea9'))

                            self.bluetooth_server.write_data_only_to_storage(close_disturbing_peaks, 'hea10')
#                             asyncio.run(self.bluetooth_server.write_data_only_to_storage(close_disturbing_peaks, 'hea10'))

                            found_peak_index = np.argmax(np.array(self.peak_weighted))
                            found_heart_freq = peak_freq[found_peak_index]
                            found_heart_freq_amplitude_old = self.peak_amplitude[found_peak_index]

                            data_to_write_in_hea6 += str(found_peak_index) + "," + \
                                                     str(found_heart_freq) + "," + \
                                                     str(found_heart_freq_amplitude_old) + ","

                            # Determine the reliability of the found peak, if it's really the heart rate or just noise.
                            # Compares to the next largest peak amplitude
                            try:
                                next_largest_peak_amplitude = np.amax(
                                    self.peak_amplitude[:found_peak_index]+self.peak_amplitude[found_peak_index+1:])
                            except:
                                next_largest_peak_amplitude = -35

                            data_to_write_in_hea6 += str(next_largest_peak_amplitude) + ","

                            if found_heart_freq_amplitude_old - next_largest_peak_amplitude > 12:
                                found_peak_reliability = "ExceptionalHigh"
                                found_peak_reliability_int = 6
                            elif found_heart_freq_amplitude_old - next_largest_peak_amplitude > 7:
                                found_peak_reliability = "VeryHigh"
                                found_peak_reliability_int = 5
                            elif found_heart_freq_amplitude_old - next_largest_peak_amplitude > 4:
                                found_peak_reliability = "High"
                                found_peak_reliability_int = 4
                            elif found_heart_freq_amplitude_old - next_largest_peak_amplitude > 3:
                                found_peak_reliability = "Medium"
                                found_peak_reliability_int = 3
                            else:
                                found_peak_reliability = "Low"  # TODO uncertain?
                                found_peak_reliability_int = 2

#                             if len(close_peaks) > 1:
                            if len(close_peaks) >= 4:  # case for self.T_resolution = 40
                                print('averaging, old:', found_heart_freq)
                                found_heart_freq = np.mean(close_peaks)

#                             if len(close_disturbing_peaks) > 3 and found_heart_freq_old > 1:
                            if len(close_disturbing_peaks) >= 8 and found_heart_freq_old > 1:  # case for self.T_resolution = 40
                                # To many disturbing peaks around, can't identify the correct one
                                #print('Too many disturbing peaks around, can\'t identify the correct one')
                                found_heart_freq = found_heart_freq_old
                                found_peak_reliability = "VeryLow"
                                found_peak_reliability_int = 1

                            old_heart_freq_list.append(found_heart_freq)  # save last 20 values
#                             if len(old_heart_freq_list) > 5:
                            if len(old_heart_freq_list) > self.upl_of_old_heart_freq_list:
                                old_heart_freq_list.pop(0)

                            self.bluetooth_server.write_data_only_to_storage(old_heart_freq_list, 'hea11')
#                             asyncio.run(self.bluetooth_server.write_data_only_to_storage(old_heart_freq_list, 'hea11'))

#                             if np.abs(np.mean(old_heart_freq_list[
#                                               0:-2]) - found_heart_freq) > 0.1:  # too big change, probably noise or other disruptions
#                             if np.abs(np.mean(old_heart_freq_list[0:-2]) - found_heart_freq) > 0.05 \
                            if np.abs(np.mean(old_heart_freq_list[0:-2]) - found_heart_freq) > 0.1 \
                                and len(old_heart_freq_list) >= self.upl_of_old_heart_freq_list:  # too big change, probably noise or other disruptions (except until old_heart_freq_list is filled with measured values.)
                                found_heart_freq = np.mean(old_heart_freq_list)
                                #print('Too big change, probably noise or other disruptions, old:', old_heart_freq_list[-1])

                        except Exception as e:
                            print('exept in heart peak:', e)
                            found_heart_freq = 0

                        if first_real_value and (found_heart_freq > 1 or time.time() - start_time > 120):
                            first_real_value = False
                        if found_heart_freq < 1 and first_real_value:  # Do not trigger on the large noise peak under 1 Hz
                            found_heart_freq = 0

                        found_heart_freq_old = found_heart_freq
#                     elif len(peak_freq) > 0 and np.amin(peak_amplitude) > -40:
                    elif len(peak_freq) > 0 and np.amin(peak_amplitude) > -45:
                        found_heart_freq = found_heart_freq_old  # just use the last values
                        found_peak_reliability = "VeryLow"
                        found_peak_reliability_int = 1

                        data_to_write_in_hea6 += "," + str(found_heart_freq) + ",,,"

                    else:
                        #found_heart_freq = found_heart_freq_old
                        found_heart_freq = 0
                        self.peak_weighted.clear()
                        found_peak_reliability = "None"
                        found_peak_reliability_int = 0

                        data_to_write_in_hea6 += "," + str(found_heart_freq) + ",,,"

                    data_to_write_in_hea6 += str(found_heart_freq) + ","

                    if not measurement_data_stable_state:
                        if len(old_heart_freq_list) >= self.upl_of_old_heart_freq_list and found_heart_freq >= 50/60 and found_heart_freq < 100/60:
                            measurement_data_stable_state = True

                    if not first_real_value:
#                         print("Found heart rate Hz and BPM: ", found_heart_freq, int(
#                             60*found_heart_freq), 'Reliability:', found_peak_reliability)
#                         found_heart_rate = int(60 * found_heart_freq)
                        found_heart_rate_dcml = Decimal(str(60 * found_heart_freq)).quantize(Decimal(str(10**(-2))), rounding=ROUND_HALF_UP)
                        found_heart_rate = float(found_heart_rate_dcml)
                        print("Found heart rate Hz and BPM: ", found_heart_freq, found_heart_rate, 'Reliability:', found_peak_reliability)
                        # Do not notify clients until measurement data is stable
                        if measurement_data_stable_state:
                            self.bluetooth_server.write_data_to_app(
                                str(found_heart_rate) + ' ' + found_peak_reliability, 'heart rate')  # Send to app
#                             asyncio.run(self.bluetooth_server.write_data_to_app(
#                                 str(found_heart_rate) + ' ' + found_peak_reliability, 'heart rate'))  # Send to app

                    else:
                        print("Waiting to find heart rate")
                        found_heart_rate = 0
                        found_peak_reliability = "None"
                        found_peak_reliability_int = 0

                    data_to_write_in_hea6 += str(found_heart_rate)
                    self.bluetooth_server.write_data_only_to_storage(data_to_write_in_hea6, 'hea6')
#                     asyncio.run(self.bluetooth_server.write_data_only_to_storage(data_to_write_in_hea6, 'hea6'))

                    # BPM_search = self.freq * 60 # Used where?
                    # print("past plot heart rate")

                    # increment counters in loop
                    if FFT_counter < self.number_of_old_FFT:
                        FFT_counter += 1
                    index_in_FFT_old_values += 1
                    if index_in_FFT_old_values == self.number_of_old_FFT:
                        index_in_FFT_old_values = 0
                    # initiate save to CSV'
                    # print("time for csv write List: ",
                    #      self.list_of_variables_for_threads["start_write_to_csv_time"])
                    if self.initiate_write_heart_rate and time.time() - self.list_of_variables_for_threads["start_write_to_csv_time"] < 5*60:
                        print("Inside save to csv statement")
                        # self.heart_rate_spectrum.append(self.FFTamplitude)
                        # self.heart_rate_frequency.append(self.FFTfreq)
                        self.heart_rate_csv.append(found_heart_rate)
                        self.heart_rate_reliability_csv.append(found_peak_reliability_int)
                    elif self.initiate_write_heart_rate:
                        np_csv = np.asarray(self.heart_rate_csv)
                        np.savetxt("heart_rate.csv", np_csv, delimiter=";")
                        np_csv = np.asarray(self.heart_rate_reliability_csv)
                        np.savetxt("heart_rate_reliability.csv", np_csv, delimiter=";")
                        print("Should have saved CSV")
                        #self.go.pop(0)
                        #self.list_of_variables_for_threads["go"] = self.go
                        # np_csv = np.asarray(self.heart_rate_csv)
                        # np.savetxt("heart_rate.csv", np_csv, delimiter=";")
                        # np_csv = np.asarray(self.heart_rate_reliability_csv)
                        # np.savetxt("heart_rate_reliability.csv", np_csv, delimiter=";")
                        # print("Should have saved CSV")
                        # Remove Bluetooth clients
                        # for client in self.bluetooth_server.client_list:
                        #     print('try to remove client ' +
                        #           str(self.bluetooth_server.address_list[self.bluetooth_server.client_list.index(client)]))
                        #     client.close()
                        #     print('remove client ' +
                        #           str(self.bluetooth_server.address_list[self.bluetooth_server.client_list.index(client)]))
                        # self.bluetooth_server.server.close()
                        # print("server is now closed")
                        # os.system("echo 'power off\nquit' | bluetoothctl")

                    sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_hre_prctim_csv"], dt_stlp, "heart_rate()_while_loop_time")
#                     sv.clc_elpsd_tim(self.bluetooth_server, "sgp_hre_prctim_csv", dt_stlp, "heart_rate()_while_loop_time")

        print("Out of pulse")

    def mean_of_old_values(self, FFT_counter):  # Check
        FFT_average_over = np.zeros(int(self.total_fft_length/2))
        for columns in range(0, int(self.total_fft_length/2)):
            for rows in range(0, self.number_of_old_FFT):
                FFT_average_over[columns] = self.FFT_old_values[rows][columns] + \
                    FFT_average_over[columns]
        #print("Mean of old values: ", self.FFT_average_out / FFT_counter)
        return FFT_average_over / FFT_counter

    ### windowedFFT ###
    # input:
    # fft_window: array to be filled with filtered data. And then to be fft:d
    # overlap: how many overlapping values between two consecutive fft windows. [in percentage]
    # beta: shape factor for kaiser window.
    # returns:
    # freq: corresponding frequency array
    # fft_signal_out: fft:d array

    def windowedFFT(self):
        # window_width = len(fft_window)  # size of each window
        # window_slide = int(np.round(window_width*(1-overlap/100)))  # number of overlapping points

        dt_stlp = datetime.datetime.now()

        # print("Window slide: ", window_slide)
        for i in range(self.window_slide):  # fills the fft_window array with window_slide values from filtered queue
#             sv.print_memory_full_info(sv.list_of_variables_for_threads["f_mem_csv"], 'windowedFFT:before_bandpass_filtered_data_HR_get')
            self.fft_window[self.index_fft] = self.HR_filtered_queue.get()
#             sv.print_memory_full_info(sv.list_of_variables_for_threads["f_mem_csv"], 'windowedFFT:after_bandpass_filtered_data_HR_get')
            self.index_fft += 1
            if self.index_fft == self.window_width:
                self.index_fft = 0

        sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_hre_prctim_csv"], dt_stlp, "get_HR_filtered_queue")
#         sv.clc_elpsd_tim(self.bluetooth_server, "sgp_hre_prctim", dt_stlp, "get_HR_filtered_queue")

        # TODO: Check if necessary. # roll the matrix so that the last inserted value is to the right.
        self.fft_window = np.roll(self.fft_window, -(self.index_fft+1))
        fft_signal_out = self.smartFFT()  # do fft
        # TODO: check if necessayr. # roll the matrix back
        self.fft_window = np.roll(self.fft_window, (self.index_fft+1))

        sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_hre_prctim_csv"], dt_stlp, "windowedFFT()")
#         sv.clc_elpsd_tim(self.bluetooth_server, "sgp_hre_prctim", dt_stlp, "windowedFFT()")

        return fft_signal_out

    ### smartFFT ###
    # input:
    # signal_in: in signal as an array
    # beta: shape factor for the window
    # returns:
    # freq: frequency array [Hz]
    # signal_out: fft of the in signal as an array

    def smartFFT(self):  # "signal_in" is "fft_window"
        # print("In smartFFT")
        # length_seq = len(signal_in)  # number of sequences
        window = np.kaiser(self.window_width, self.beta)  # beta: shape factor
        self.fft_window = np.multiply(self.fft_window, window)
        # two-sided fft of input signal
        signal_in_fft = fft(self.fft_window, n=self.total_fft_length)  # ,n=2*self.window_width)
        #print("len of fft: ", len(signal_in_fft))
        signal_fft_abs = np.abs(np.divide(signal_in_fft, self.window_width))
        #print("fft abs: ", signal_fft_abs)
        signal_out = np.multiply(2, signal_fft_abs[0:self.total_fft_length//2])  # one-sided fft
        #print("Signal out: ", signal_out)
        #print("len of signal out: ", len(signal_out))
        # frequency array corresponding to frequencies in the fft
        return signal_out

    def findPeaks(self, FFT_averaged):
        # Lower and higher freq for removing unwanted areas of the FFT
        # TODO Unsure about this part, same max freq several times in a row
#         F_scan_lower = 0.8
#         F_scan_upper = 3
#         #print("len self freq: ", len(self.freq))
#         FFT_in_interval = FFT_averaged[self.freq <= F_scan_upper]
#         freq2 = self.freq[self.freq <= F_scan_upper]
#         FFT_in_interval = FFT_in_interval[freq2 > F_scan_lower]
#         peak_freq_linspace = np.linspace(F_scan_lower, F_scan_upper, num=len(FFT_in_interval))

        FFT_in_interval = FFT_averaged[self.freq <= self.F_scan_upper]
        freq2 = self.freq[self.freq <= self.F_scan_upper]
        FFT_in_interval = FFT_in_interval[freq2 > self.F_scan_lower]
        peak_freq_linspace = self.peak_freq_linspace

        #print("len of fft in interval: ", len(FFT_in_interval))
        #print("FFT_in_interval", FFT_in_interval, "\n", len(FFT_in_interval))

        MaxFFT = np.amax(FFT_in_interval)  # Do on one line later, to remove outliers
        #threshold = MaxFFT - 10
#         threshold = -35
        threshold = -40
        peaks, _ = signal.find_peaks(FFT_in_interval)

        print('len(peaks) = ' + str(len(peaks)))  # for debug

        index_list = []
        index = 0
        for peak in peaks:
            if FFT_in_interval[peak] < threshold:
                index_list.append(index)
            index += 1
        peaks = np.delete(peaks, index_list)

        #print("Peaks: ",)
        self.peak_freq = []  # Maybe change to array?
        for i in peaks:
            self.peak_freq.append(peak_freq_linspace[i])
        #print("Found peak freq: ", self.peak_freq)

        self.peak_amplitude = []
        for i in peaks:
            self.peak_amplitude.append(FFT_in_interval[i])

        # Plotting for FFT
        self.FFTfreq = peak_freq_linspace
        self.FFTamplitude = FFT_in_interval
        self.len_fft = int(len(FFT_in_interval))
        #print("Length of fft:", self.len_fft)
        return self.peak_freq, self.peak_amplitude

    # TODO Used for plotting in main, remove later
    def getFFTvalues(self):
        return self.FFTfreq, self.FFTamplitude, self.peak_freq, self.peak_amplitude, self.len_fft, self.peak_weighted

    def blood_pressure(self):
        while sv.list_of_variables_for_threads["terminate_yet"]:

#             while self.go:
            if sv.list_of_variables_for_threads["is_measuring"]:

                val = 0
                pval = 0
                movavgHRdata = []
                idx0 = 1
                idxpeak0 = 0
                state = 0

                while True:
                    pval = val
                    val = self.HR_filtered_queue_movavg.get()

                    if val >= 0 and pval < 0:
                        movavgHRdata.append(pval)
                        movavgHRdata.append(val)
                        self.bluetooth_server.write_data_only_to_storage(str(movavgHRdata[-2]) + ',,,,,,', 'bpint')
#                         asyncio.run(self.bluetooth_server.write_data_only_to_storage(str(movavgHRdata[-2]) + ',,,,,,', 'bpint'))
                        self.bluetooth_server.write_data_only_to_storage(str(movavgHRdata[-1]) + ',,,,,,', 'bpint')
#                         asyncio.run(self.bluetooth_server.write_data_only_to_storage(str(movavgHRdata[-1]) + ',,,,,,', 'bpint'))
                        break

#             while self.go:
                while True:
                    val = self.HR_filtered_queue_movavg.get()
                    movavgHRdata.append(val)
                    self.bluetooth_server.write_data_only_to_storage(str(movavgHRdata[-1]) + ',,,,,,', 'bpint')
#                     asyncio.run(self.bluetooth_server.write_data_only_to_storage(str(movavgHRdata[-1]) + ',,,,,,', 'bpint'))

                    if movavgHRdata[-2] >= 0 and movavgHRdata[-1] < 0:
                        idx0 = len(movavgHRdata)
                        peaks, _ = signal.find_peaks(movavgHRdata)
                        local_maximal = [movavgHRdata[i] for i in peaks]
                        max_local_maximal = max(local_maximal)
                        idxpeak0 = movavgHRdata.index(max_local_maximal)
                        break

#             while self.go:
                count_bp_data = 0
                while sv.list_of_variables_for_threads["is_measuring"]:

                    dt_stlp = datetime.datetime.now()

                    self.measurement_start_time =  sv.list_of_variables_for_threads["measurement_start_time"]
                    if state == 0 and movavgHRdata[-2] < 0 and movavgHRdata[-1] >= 0:
                        idx1 = len(movavgHRdata)
                        tempList = movavgHRdata[idx0 - 2 : idx1]
                        peaks, _ = signal.find_peaks([(-1) * listitem for listitem in tempList])
                        local_minimal = [tempList[i] for i in peaks]
                        min_local_minimal = min(local_minimal)
                        idxbottom = movavgHRdata.index(min_local_minimal)
                        state = 1
                    elif state == 1 and movavgHRdata[-2] >= 0 and movavgHRdata[-1] < 0:
                        idx2 = len(movavgHRdata)
                        tempList = movavgHRdata[idx1 - 2 : idx2]
                        peaks, _ = signal.find_peaks(tempList)
                        local_maximal = [tempList[i] for i in peaks]
                        max_local_maximal = max(local_maximal)
                        idxpeak1 = movavgHRdata.index(max_local_maximal)
                        sbp = 140 - 74 * (idxpeak1 - idxbottom) * 50 / 1000
#                         sbp = 140 - 74 * (idxpeak1 - idxbottom) * 9.6 / 1000
                        mbp = 105 - 29 * (idxpeak1 - idxpeak0) * 50 / 1000
#                         mbp = 105 - 29 * (idxpeak1 - idxpeak0) * 9.6 / 1000
                        dbp = (3 * mbp - sbp) / 2
                        sbp_movavg = self.movavg_SBP.filter(sbp)
                        mbp_movavg = self.movavg_MBP.filter(mbp)
                        dbp_movavg = self.movavg_DBP.filter(dbp)
                        if count_bp_data < self.window_size_for_bp_movavg:
                            count_bp_data += 1
                        if count_bp_data >= self.window_size_for_bp_movavg:
                            self.bluetooth_server.write_data_to_app(
#                             asyncio.run(self.bluetooth_server.write_data_to_app(
                                str(sbp) + ' ' + str(mbp) + ' ' + str(dbp) + ' ' \
                                 + str(sbp_movavg) + ' ' + str(mbp_movavg) + ' ' + str(dbp_movavg), 'blood pressure')  # Send to app
#                                + str(sbp_movavg) + ' ' + str(mbp_movavg) + ' ' + str(dbp_movavg), 'blood pressure'))  # Send to app
                        self.bluetooth_server.write_data_only_to_storage(
#                         asyncio.run(self.bluetooth_server.write_data_only_to_storage(
                            str(movavgHRdata[-1]) + ',' \
                            + str(idxpeak0) + ',' + str(idxbottom) + ',' + str(idxpeak1) + ',' \
                            + str(sbp) + ',' + str(mbp) + ',' + str(dbp), 'bpint')
#                             + str(sbp) + ',' + str(mbp) + ',' + str(dbp), 'bpint'))
                        state = 0
                        del movavgHRdata[0 : idx1 - 2]
                        idx0 = len(movavgHRdata) - 1
                        idxpeak0 = idxpeak1 - idx1 + 2

                    dt_tmp = datetime.datetime.now()

#                     sv.print_memory_full_info(sv.list_of_variables_for_threads["f_mem_csv"], 'blood_pressure:before_HR_filtered_queue_movavg_get')
                    val = self.HR_filtered_queue_movavg.get()
#                     sv.print_memory_full_info(sv.list_of_variables_for_threads["f_mem_csv"], 'blood_pressure:after_HR_filtered_queue_movavg_get')

                    sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_bpe_prctim_csv"], dt_tmp, "get_HR_filtered_queue_movavg")
#                     sv.clc_elpsd_tim(self.bluetooth_server, "sgp_bpe_prctim", dt_tmp, "get_HR_filtered_queue_movavg")

                    movavgHRdata.append(val)
                    if not (state == 1 and movavgHRdata[-2] >= 0 and movavgHRdata[-1] < 0):
                        self.bluetooth_server.write_data_only_to_storage(str(movavgHRdata[-1]) + ',,,,,,', 'bpint')
#                         asyncio.run(self.bluetooth_server.write_data_only_to_storage(str(movavgHRdata[-1]) + ',,,,,,', 'bpint'))

                    sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_bpe_prctim_csv"], dt_stlp, "blood_pressure()_while_loop_time")
#                     sv.clc_elpsd_tim(self.bluetooth_server, "sgp_bpe_prctim", dt_stlp, "blood_pressure()_while_loop_time")

        print("out of blood_pressure")

    def schmittTrigger(self):
        while sv.list_of_variables_for_threads["terminate_yet"]:

            if sv.list_of_variables_for_threads["is_measuring"]:

#                 print("SchmittTrigger started")
                # Test for time
                Inside = True
                # variable declaration
#                 Tc = 12  # medelvärdesbildning över antal [s]
#                 Tc = 6  # medelvärdesbildning över antal [s]  # Changed value from 12 to 6 to prevent respiration rate from reaching 0.
                Tc = 4  # medelvärdesbildning över antal [s]  # Changed value from 12 to 4 to prevent respiration rate from reaching 0.
                schNy = 0  # Schmitt ny
                schGa = 0  # Schmitt gammal
                Hcut = 0.001  # Higher hysteres cut. Change this according to filter. To manage startup of filter
                Lcut = -Hcut  # Lower hysteres cut
                # average over old values. TODO ev. ingen medelvärdesbildning. För att förhindra att andningen går mot ett fast värde. Vi vill se mer i realtid.
                avOver = 8
                freqArray = np.zeros(avOver)  # for averaging over old values
                count = 1  # for counting number of samples passed since last negative flank
                countHys = 1  # for counting if hysteresis should be updated
                FHighRR = 0.7  # To remove outliers in mean value
                FLowRR = 0.1  # To remove outliers in mean value
                # for saving respiratory_queue_RR old values for hysteresis
#                 trackedRRvector = np.zeros(self.sample_freq * Tc)  # to save old values
                trackedRRvector = np.zeros(int(self.sample_freq) * Tc)  # to save old values
                # Added for holding last sent data
                respiratory_rate_data = 0
                # A variable that indicates when the measurement data is stable
                measurement_data_stable_state = False

#                 while self.go:
                while sv.list_of_variables_for_threads["is_measuring"]:

                    dt_stlp = datetime.datetime.now()

                    data_to_write_in_sch = ""


                    # to be able to use the same value in the whole loop
#                     if self.time_when_sent_last_value is not None and (time.time() - self.time_when_sent_last_value > 10):
#                         # sends zero as breath rate if no value was found the last ten seconds
                    if self.time_when_sent_last_value is not None and (time.time() - self.time_when_sent_last_value > 20):
                        # sends zero as breath rate if no value was found the last twenty seconds
#                     if self.time_when_sent_last_value is not None and (time.time() - self.time_when_sent_last_value > 14):
#                         # sends zero as breath rate if no value was found the last fourteen seconds
                        self.bluetooth_server.write_data_to_app(0, 'breath rate')
#                         asyncio.run(self.bluetooth_server.write_data_to_app(0, 'breath rate'))
#                         # sends last breath rate if no value was found the last ten seconds
#                         self.bluetooth_server.write_data_to_app(respiratory_rate_data, 'breath rate')
                        self.time_when_sent_last_value = time.time()
                        # For the time being, I tried the same
                        count = 0

                    dt_tmp = datetime.datetime.now()

#                     sv.print_memory_full_info(sv.list_of_variables_for_threads["f_mem_csv"], 'schmittTrigger:before_RR_filtered_queue_get')
                    trackedRRvector[countHys - 1] = self.RR_filtered_queue.get()
#                     sv.print_memory_full_info(sv.list_of_variables_for_threads["f_mem_csv"], 'schmittTrigger:after_RR_filtered_queue_get')

                    sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_rre_prctim_csv"], dt_tmp, "get_RR_filtered_queue")
#                     sv.clc_elpsd_tim(self.bluetooth_server, "sgp_rre_prctim", dt_tmp, "get_RR_filtered_queue")

                    data_to_write_in_sch += str(countHys) + " " + str(trackedRRvector[countHys - 1]) + " "

                    #print("Amplitude for respitory rate {}".format(trackedRRvector[countHys-1]))
                    # self.RTB_final_queue.put(trackedRRvector[countHys - 1])

                    if countHys == self.sample_freq * Tc:
                        Hcut = np.sqrt(np.mean(np.square(trackedRRvector))) * 0.7  # rms of trackedRRvector
                        # Hcut = 0.002
                        if Hcut < 0.1:
                            Hcut = 0.1
                        Lcut = -Hcut

                        # print("Hcut: ", Hcut)       # se vad hysteres blir
                        # print("The last value of vector {}".format(trackedRRvector[countHys-1]))
                        # TODO Hinder så att insvängningstiden för filtret hanteras
                        countHys = 0

                    data_to_write_in_sch += str(Hcut) + " " + str(Lcut) + " "

                    # schNy = schGa   behövs inte. Görs nedan

                    # trackedRRvector[countHys-1] is the current data from filter
                    # Takes long time to go into this loop
                    if trackedRRvector[countHys - 1] <= Lcut:
                        schNy = 0
                        if schGa == 1:
                            # print("Inside update resprate loop")
#                             np.roll(freqArray, 1)
                            freqArray = np.roll(freqArray, 1)
                            # save the new frequency between two negative flanks
                            freqArray[0] = self.sample_freq / count
                            # Take the mean value
                            # RR_final_queue is supposed to be the breathing rate queue that is sent to app
                            # self.RR_final_queue.put(self.getMeanOfFreqArray(freqArray, FHighRR, FLowRR))
                            # start = time.time()
#                             self.bluetooth_server.write_data_to_app(
#                                 self.getMeanOfFreqArray(freqArray, FHighRR, FLowRR), 'breath rate')
                            # Split processing to keep transmitted data
                            respiratory_rate_data = self.getMeanOfFreqArray(freqArray, FHighRR, FLowRR)
                            if not measurement_data_stable_state:
                                # Check if all elements of freqArray are greater than 0
                                for freqArrayItem in freqArray:
                                    if freqArrayItem > 0:
                                        measurement_data_stable_state = True
                                    else:
                                        measurement_data_stable_state = False
                                        break
                                if respiratory_rate_data < 12 or respiratory_rate_data > 20:
                                    measurement_data_stable_state = False
                            # Do not notify clients until measurement data is stable
                            if measurement_data_stable_state:
                                self.bluetooth_server.write_data_to_app(respiratory_rate_data, 'breath rate')
#                                 asyncio.run(self.bluetooth_server.write_data_to_app(respiratory_rate_data, 'breath rate'))
                            self.time_when_sent_last_value = time.time()
                            # done = time.time() # verkar ta lite tid, troligtvis på grund av getMeanOfFrequency
                            # print('send to app', (done - start)*1000)

                            # TODO put getMeanOfFreqArray() into queue that connects to send bluetooth values instead
                            count = 0
                    # trackedRRvector[countHys-1] is the current data from filter
                    elif trackedRRvector[countHys - 1] >= Hcut:
                        schNy = 1

                    for freq in freqArray:
                        data_to_write_in_sch += str(freq) + " "

                    data_to_write_in_sch += str(FHighRR) + " " + str(FLowRR) + " " + str(respiratory_rate_data) + " " + \
                                            str(schNy) + " " + str(schGa) + " " + str(count)
                    self.bluetooth_server.write_data_only_to_storage(data_to_write_in_sch, 'sch')
#                     asyncio.run(self.bluetooth_server.write_data_only_to_storage(data_to_write_in_sch, 'sch'))

                    schGa = schNy
                    count += 1
                    countHys += 1

                    end = time.time()
                    # print("Tid genom schmittTrigger: ", end-start)

                    sv.clc_elpsd_tim(sv.list_of_variables_for_threads["f_sgp_rre_prctim_csv"], dt_stlp, "schmittTrigger()_while_loop_time")
#                     sv.clc_elpsd_tim(self.bluetooth_server, "sgp_rre_prctim", dt_stlp, "schmittTrigger()_while_loop_time")

        print("out of schmittTrigger")

    # Used in schmittTrigger. Removes outliers and return mean value over last avOver values.
    def getMeanOfFreqArray(self, freqArray, FHighRR, FLowRR):  # remove all values > FHighRR and < FLowRR
        self.time = time.time()
        # print("Since last time {}".format(self.time - self.last_time))
        self.last_time = self.time
        start = time.time()
        # freqArrayTemp = [x for x in freqArray if (x < FHighRR and x > FLowRR)]
        index_list = []
        index = 0
        # print("Before removal: Array {} \n Low and high hyst {},{}".format(freqArray, FLowRR, FHighRR))
        for freq_value in freqArray:
            if freq_value < FLowRR or freq_value > FHighRR or freq_value == 0:
                index_list.append(index)
            index += 1
        freqArrayTemp = np.delete(freqArray, index_list)
        # print("After removal but before deviation: ", freqArrayTemp)
        # freqArrayTemp = [x for x in freqArrayTemp if x != 0]
        # print(non_zero_temp)
        # print(type(non_zero_temp))
        # freqArrayTemp = freqArrayTemp[non_zero_temp]
        # a[nonzero(a)]

        median = np.median(freqArrayTemp)  # median value
        stanDev = np.std(freqArrayTemp)  # standard deviation

        # freqArrayTemp = [x for x in freqArrayTemp if (
        #    x > median - 3 * stanDev and x < median + 3 * stanDev)]
        # print(freqArrayTemp)
        index_list = []
        index = 0
        for freq_value in freqArrayTemp:
            if freq_value < median - 3 * stanDev and freq_value > median - 3 * stanDev:
                index_list.append(index)
            index += 1
        freqArrayTemp = np.delete(freqArrayTemp, index_list)
        # print("Last array before mean value {}".format(freqArrayTemp))
        # if len(freqArrayTemp) == 0:
        #     freqArrayTemp = self.freqArrayTemp_last
        # else:
        #     self.freqArrayTemp_last = freqArrayTemp
        mean = np.mean(freqArrayTemp)  # mean value of last avOver values excluding outliers
        # mean is nan if FreqArrayTemp is zero, which creates error when sending data to app
        if len(freqArrayTemp) == 0:
            mean = 0        # TODO ta det föregående värdet istället
            print("No values left in freqArrayTemp")
        mean = mean * 60  # To get resp rate in Hz to BPM
        mean = int(np.round(mean))
        # print("data from schmitt {}".format(mean))
        end = time.time()
        # print("Time through getMeanFreq {}".format(end-start))
        return mean


# MAIN ##  TODO: Ta bort MAIN sen


# #windowedFFT(data_in, sample_freq, T_resolution, overlap, beta)
# HR_filtered_queue = queue.Queue()
# HR_final_queue = queue.Queue()
# RR_filtered_queue = queue.Queue()
# RR_final_queue = queue.Queue()


# sample_freq = 20
# length_seq = 100000
# sample_spacing = 1/sample_freq

# t = np.arange(length_seq)*sample_spacing
# signal_in = 4*np.sin(1 * 2.0*np.pi*t) + 0*np.sin(2 * 2.0*np.pi*t)
# # print(signal_in)

# for i in range(len(signal_in)):
#     HR_filtered_queue.put(signal_in[i])
#     RR_filtered_queue.put(signal_in[i])

# go = ["True"]

# signal_processing = SignalProcessing(
#     go, HR_filtered_queue, HR_final_queue, RR_filtered_queue, RR_final_queue)

# time.sleep(0.5)
# go.pop(0)


#### Test av smartFFT ####
# sample_freq = 20
# length_seq = 600
# sample_spacing = 1/sample_freq

# t = np.arange(length_seq)*sample_spacing
# signal_in = 4*np.sin(1 * 2.0*np.pi*t) + 0.5*np.sin(4 * 2.0*np.pi*t)
# #signal_in = np.roll(signal_in, 5)
# beta = 1

# [freq,signal_out] = smartFFT(signal_in,sample_freq,beta)

# plt.plot(freq, signal_out)
# plt.grid()
# plt.show()
