import numpy as np
import csv
import scipy.io as sp
import time as timer

from acconeer_utils.clients.reg.client import RegClient
from acconeer_utils.clients.json.client import JSONClient
from acconeer_utils.clients import configs
from acconeer_utils import example_utils
from acconeer_utils.mpl_process import PlotProcess, PlotProccessDiedException, FigureUpdater


def main():
    args = example_utils.ExampleArgumentParser().parse_args()
    example_utils.config_logging(args)
    if args.socket_addr:
        client = JSONClient(args.socket_addr)
    else:
        port = args.serial_port or example_utils.autodetect_serial_port()
        client = RegClient(port)
    client.squeeze = False

    # Setup parameters
    filename = "Manniska_lang_0305_Test2.csv"
    config = setup_parameters()
    time = 10
    seq = config.sweep_rate * time
    config.sensor = args.sensors
    info = client.setup_session(config)
    num_points = info["data_length"]
    # print(num_points)
    info_file(filename, config, num_points, time, seq)  # Setup info file

    matris = np.zeros((seq, num_points), dtype=np.csingle)
    client.start_streaming()
    print("Starting...")

    start = timer.time()
    for i in range(0, seq):
        info, sweep = client.get_next()
        matris[0][:] = sweep[:]
        matris = np.roll(matris, 1, axis=0)
    end = timer.time()
    print(i+1)
    print((end - start), "s")
    # print("Disconnecting...")
    #np.savetxt(filename, matris, delimiter=";")
    client.disconnect()


def setup_parameters():
    config = configs.IQServiceConfig()
    config.range_interval = [0.5, 0.7]
    config.sweep_rate = 25
    config.gain = 1
    #config.running_average_factor = 0.5
    return config


def info_file(filename, config, num_points, time, seq):
    with open("Info_"+filename, "w", newline='\n') as result:
        writer = csv.writer(result, delimiter=';')
        writer.writerow(["Gain: ", str(config.gain)])
        writer.writerow(["Min range:", str(config.range_interval[0])])
        writer.writerow(["Max range:", str(config.range_interval[1])])
        writer.writerow(["Data length:", str(num_points)])
        writer.writerow(["Freq: ", str(config.sweep_rate)])
        writer.writerow(["Tejp: ", "Människa. Puls referens 50-60 BPM"])
        writer.writerow(["Tid: ", time])
        writer.writerow(["Sekvenser: ", seq])


if __name__ == "__main__":
    main()
