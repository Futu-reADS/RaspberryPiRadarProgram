import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
# import scipy as sp
from scipy import signal

from acconeer_utils.clients.reg.client import RegClient
from acconeer_utils.clients.json.client import JSONClient
from acconeer_utils.clients import configs
from acconeer_utils import example_utils
from acconeer_utils.mpl_process import PlotProcess, PlotProccessDiedException, FigureUpdater


def main():
    args = example_utils.ExampleArgumentParser(num_sens=1).parse_args()
    example_utils.config_logging(args)

    if args.socket_addr:
        client = JSONClient(args.socket_addr)
    else:
        port = args.serial_port or example_utils.autodetect_serial_port()
        client = RegClient(port)

    config = config_setup()
    config.sensor = args.sensors
    info = client.setup_session(config)
    num_points = info["data_length"]
    tracking = Tracking(num_points, config.range_interval)

    amplitude_y_max = 22000

    fig, (amplitude_ax) = plt.subplots(1)
    fig.set_size_inches(12, 6)
    fig.canvas.set_window_title("filename")

    for ax in [amplitude_ax]:
        ax.set_xlabel("Depth (m)")
        ax.set_xlim(config.range_interval)

    amplitude_ax.set_ylabel("Amplitude")
    amplitude_ax.set_ylim(0, amplitude_y_max)

    xs = np.linspace(*config.range_interval, num_points)
    amplitude_line = amplitude_ax.plot(xs, np.zeros_like(xs))[0]

    fig.tight_layout()
    plt.ion()
    plt.show()

    interrupt_handler = example_utils.ExampleInterruptHandler()
    print("Press Ctrl-C to end session")

    client.start_streaming()
    counter = 0
    while not interrupt_handler.got_signal:
        info, sweep = client.get_next()
        amplitude = np.abs(sweep)
        track = tracking.tracking(sweep, counter)
        counter += 1
        print(track)
        # amplitude_line.set_ydata(track)
        amplitude_line.set_ydata(amplitude)
        fig.canvas.flush_events()

    print("Disconnecting...")
    client.disconnect()


def config_setup():
    config = configs.IQServiceConfig()
    config.range_interval = [0.3, 0.7]
    config.sweep_rate = 1
    config.gain = 1
    #config.session_profile = configs.EnvelopeServiceConfig.MAX_DEPTH_RESOLUTION
    # config.session_profile = configs.EnvelopeServiceConfig.MAX_SNR
    print(config.gain)
    return config


class Tracking:
    def __init__(self, num_points, range_interval):
        self.num_points = num_points
        self.config_range_interval = range_interval
        self.I_peaks = np.zeros((1, self.num_points))
        self.locks = np.zeros((1, self.num_points))
        self.I_peaks_filtered = np.zeros((1, self.num_points))
        self.tracked_distance = np.zeros((1, self.num_points))
        self.tracked_amplitude = np.zeros((1, self.num_points))
        self.tracked_phase = np.zeros((1, self.num_points))
        self.data_matrix = np.zeros((1, self.num_points))

        # self.data_idx = configs["data_index"]

    def tracking(self, data, data_idx):
        self.data = data
        self.data_idx = data_idx
        counter = 0  # Used only for if statement only for first iteration and not when data_idx goes back to zero
        N_avg = 10  # Number of total peaks to average over
        self.start_distance = 0.37  # Initial guess for where
        # self.data_matrix[self.data_idx][:] = self.data
        dist = self.num_points     # number of datapoints in data # self.num_points
        # maximum value
        interval = self.config_range_interval[1] - self.config_range_interval[0]

        if self.data_idx == 0 and counter == 0:      # things that only happens first time
            # chooses index closest to starting distance
            I = np.round(
                ((self.start_distance - self.config_range_interval[0]) / interval) * dist)

            # I = np.abs(self.data).index(signal.find_peaks(np.abs(self.data)))
            I_idx = np.argmax(self.data)
            # print(I)
            # print(I_idx)
            # print(dist)

            # self.I_peaks[0][0] = I

            self.locks, _ = signal.find_peaks(np.abs(self.data))
            print(self.locks)
            print(I_idx)
            # print(self.locks)  # Check what happends during the first cycle.
            # I = np.amin(np.abs(self.locks - self.I_peaks[0][0]))
            # print(self.I_peaks)
            # print(I, int(I))
            self.I_peaks[0][0] = I
            # print(self.I_peaks[0][0])
            # print(type(I), type(int(I)))
            self.I_peaks_filtered[0][0] = self.I_peaks[0][0]
            self.tracked_distance[0][0] = self.I_peaks_filtered[0][0] / dist * interval
            self.tracked_amplitude[0][0] = np.abs(self.data[int(self.I_peaks_filtered[0][0])])

            self.tracked_phase[0][0] = np.angle(self.data[int(self.I_peaks_filtered[0][0])])

        # After first seq continous tracking
        else:
            self.locks = None
            self.locks, _ = signal.find_peaks(np.abs(self.data))
            I = np.amin(self.locks - self.I_peaks_filtered[0][self.data_idx - 1])
            last_max = self.I_peaks_filtered[0][self.data_idx - 1]
            List_of_largest_amp = [np.abs(self.data[int(I + last_max)]),
                                   np.abs(self.data[int(last_max-I)])]
            if List_of_largest_amp[0] > List_of_largest_amp[1]:
                I = I + last_max
            else:
                I = last_max - I

            if self.locks == None:
                self.I_peaks[0][self.data_idx] = self.I_peaks[0][self.data_idx-1]
            else:
                self.I_peaks[0][self.data_idx] = I

            if counter == 0:
                self.i_avg_start = np.amax([0, self.data_idx - N_avg])
            else:
                self.i_avg_start = self.data_idx - N_avg
                counter = 1
            # I_avg_start to data_idx

            # for i in range(self.i_avg_start: self.data_idx):
            #   last_samples = last_samples + self.I_peaks[0][i]

            self.I_peaks_filtered[0][self.data_idx] = np.round(
                np.mean(self.I_peaks[0][self.i_avg_start:self.data_idx]))

            # print(self.I_peaks_filtered)
            # print(self.I_peaks_filtered)
            # print(self.I_peaks_filtered[0][int(self.data_idx)])
            # print(self.I_peaks_filtered[0][data_idx])
            self.tracked_distance[0][self.data_idx] = self.I_peaks_filtered[0][self.data_idx] / dist * interval
            self.tracked_distance_now = self.I_peaks_filtered[0][self.data_idx] / dist * interval
            self.tracked_amplitude[0][self.data_idx] = np.abs(
                self.data[int(self.I_peaks_filtered[0][self.data_idx])])

            # self.data(int(self.I_peaks_filtered[0][self.data_idx]))

            self.tracked_phase[0][self.data_idx] = np.angle(
                self.data[int(self.I_peaks_filtered[0][self.data_idx])])

        return self.tracked_distance


if __name__ == "__main__":
    main()
