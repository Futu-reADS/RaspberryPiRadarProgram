
# Import available classes used in main
import time
import queue
import subprocess       # For Raspberry Pi shutdown
import os               # For using terminal commands
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator
import numpy as np

import datetime

# Import our own classes used in main
import bluetooth_server_module          # Import bluetooth class for managing connections with devices
import data_acquisition_module          # Import class which collects and filters relevant data from radar
# Import signal processing class for Schmitt Trigger and Pulse detection
import signal_processing_module

import shared_variables as sv

def main():
    time.sleep(10)

    # Queues used for accessing data from different threads
    HR_filtered_queue = queue.Queue()
    HR_final_queue = queue.Queue()

    HR_filtered_queue_movavg = queue.Queue()

    RR_filtered_queue = queue.Queue()
    RR_final_queue = queue.Queue()
    RTB_final_queue = queue.Queue()  # Real time breating final queue
    heart_rate_csv = []
    initiate_write_heart_rate = []
    start_write_to_csv_time = 0
    window_slide = 1

    measurement_start_time = []

    # List of arguments and data sent between classes
    go = []       # Used for closing threads before end of this program

    shutdown_yet = ["Yes"]      # Used to indicate not yet shut down
    terminate_yet = ["Yes"]     # Used to indicate that the program is not exiting yet
    is_measuring = []           # Used to indicate that a measurement is in progress

    run_measurement = []        # Determines if data is being sent to devices or not
    sample_freq = 0         # Value is updated in DataAcquisition. Needs to be the same in the whole program
    sv.list_of_variables_for_threads = {"HR_filtered_queue": HR_filtered_queue, "HR_final_queue": HR_final_queue,
                                        "RR_filtered_queue": RR_filtered_queue, "RR_final_queue": RR_final_queue,
                                        "RTB_final_queue": RTB_final_queue, "go": go, "run_measurement": run_measurement,
                                        "sample_freq": sample_freq, "heart_rate_csv": heart_rate_csv,
                                        "window_slide": window_slide, "initiate_write_heart_rate": initiate_write_heart_rate,
                                        "start_write_to_csv_time": start_write_to_csv_time,
                                        "f_hr_csv" : None,
                                        "f_rr_csv" : None,
                                        "f_rtb_csv": None,
                                        "f_raw_csv": None,
#                                         "f_iq_csv" : f_iq_csv,
                                        "f_sch_csv": None,
                                        "f_hea1_csv": None,  # for debug
                                        "f_hea2_csv": None,  # for debug
                                        "f_hea3_csv": None,  # for debug
                                        "f_hea4_csv": None,
                                        "f_hea5_csv": None,
                                        "f_hea6_csv": None,
                                        "f_hea7_csv": None,
                                        "f_hea8_csv": None,
                                        "f_hea9_csv": None,
                                        "f_hea10_csv": None,
                                        "f_hea11_csv": None,
                                        "measurement_start_time": measurement_start_time,
                                        "shutdown_yet": shutdown_yet,
                                        "terminate_yet": terminate_yet,
                                        "is_measuring": is_measuring,
                                        "f_bp_csv": None,
                                        "f_bpint_csv": None,
                                        "HR_filtered_queue_movavg": HR_filtered_queue_movavg}
    FFTfreq = [1, 2, 3]
    FFTamplitude = [1, 2, 3]
    peak_freq = [1]
    peak_amplitude = [1]
    len_fft = 0
    array = []
    #freq_array = np.linspace(0.8*60, 180, 2*33)
    run_times = 0

    # BluetoothServer object sent to classes which sends data locally
#     bluetooth_server = bluetooth_server_module.BluetoothServer(list_of_variables_for_threads)
    bluetooth_server = bluetooth_server_module.BluetoothServer()

    # Starts thread of run() method in DataAcquisition class
#     data_acquisition = data_acquisition_module.DataAcquisition(
#         list_of_variables_for_threads, bluetooth_server)
    data_acquisition = data_acquisition_module.DataAcquisition(bluetooth_server)
    data_acquisition.start()

    # SignalProcessing object used below
#     signal_processing = signal_processing_module.SignalProcessing(
#         list_of_variables_for_threads, bluetooth_server, FFTfreq, FFTamplitude)
    signal_processing = signal_processing_module.SignalProcessing(bluetooth_server, FFTfreq, FFTamplitude)

    #plt.pcolormesh(specTime, specFreq, specSignal)
    # plt.pause(1)
    #plt.xlim(1, 3)
    # Lets threads and thereby program run while go is True. Go is set from app
#     while list_of_variables_for_threads.get('go'):
    while sv.list_of_variables_for_threads.get('terminate_yet'):
        # Test of FFT, remove later
        #plt.xlim(1, 3)
        #FFTfreq, FFTamplitude, peak_freq, peak_amplitude, len_fft, peak_weighted = signal_processing.getFFTvalues()
        #print("Length of FFT_amplitude", len(FFTamplitude))
        #if len(FFTamplitude) == len_fft:
            #time_array = np.linspace(0, (run_times+1)*1.5, run_times+1)
            # array.append(FFTamplitude)
            #plt.figure(1)
            #plt.clf()
            # try:
            #     #print('FFTfreq',len(FFTfreq), 'FFTamplitude',len(FFTamplitude))
            #     # print('peak_freq',len(peak_freq),'peak_amplitude',len(peak_amplitude),'peak_weighted',len(peak_weighted),peak_weighted)
            #     plt.plot(FFTfreq, FFTamplitude)
            #     plt.plot(peak_freq, peak_amplitude, 'bo')
            #     plt.plot(peak_freq, peak_weighted, 'ro')
            #     plt.pause(0.1)
            # except Exception as e:
            #     print('plot error:', e)

            # cmap = plt.get_cmap('PiYG')
            # levels = MaxNLocator(nbins=90).tick_values(-35, np.amax(array))
            # norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

            # plt.figure(2)
            # plt.clf()
            # plt.pcolormesh(time_array, freq_array, np.transpose(array), norm=norm)
            # plt.colorbar()
            # plt.xlabel("Time (s)")
            # plt.ylabel("Frequency (bpm)")
            # run_times += 1
        #plt.pause(0.9)
        time.sleep(1)
        # plt.plot(FFTfreq, FFTamplitude)
        # plt.plot(peak_freq, peak_amplitude, 'bo')
        # plt.plot(peak_freq, peak_weighted, 'ro')

        # time.sleep(1)
        #print(FFTfreq, FFTamplitude)

        # Waits for running threads to finish their loops
    bluetooth_server.connect_device_thread.join()
    print("bluetooth_server is closed")
    signal_processing.heart_rate_thread.join()
    print('Heart rate thread is closed')
    signal_processing.blood_pressure_thread.join()
    print("Blood pressure thread is closed")
    signal_processing.schmittTrigger_thread.join()
    print("signal_processing is closed")
    data_acquisition.join()
    print("data_acquisition is closed")

    if not sv.list_of_variables_for_threads.get('shutdown_yet'):
        print('Shut down succeed')
        #subprocess.call(["sudo", "shutdown", "-r", "now"])         # Terminal command for shutting down Raspberry Pi
        os.system("sudo shutdown -h now")


if __name__ == "__main__":      # Required for making main method the used main-method
    main()
