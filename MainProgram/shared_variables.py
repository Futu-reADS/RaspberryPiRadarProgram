import datetime
import psutil
# import asyncio

list_of_variables_for_threads = {}

def clc_elpsd_tim(f_csv, prv_tim, msg):
    cur_tim = datetime.datetime.now()
    if list_of_variables_for_threads["run_measurement"]:
        if list_of_variables_for_threads["is_measuring"]:
            if not f_csv.closed:
                elpsd_tim = cur_tim - prv_tim
                f_csv.write(str(cur_tim) + ' ' + str(elpsd_tim.total_seconds() * 1000) + ' ' + msg + '\n')
    return cur_tim

def print_memory_full_info(f_csv, msg):
    if not hasattr(print_memory_full_info, "prv_tim"):
        print_memory_full_info.prv_tim = datetime.datetime.now()  # Initialize
    cur_tim = datetime.datetime.now()
    mem_info = psutil.Process().memory_full_info()
    if list_of_variables_for_threads["run_measurement"]:
        if list_of_variables_for_threads["is_measuring"]:
            if f_csv is None:
                pass
            elif not f_csv.closed:
                interval_time = cur_tim - print_memory_full_info.prv_tim
                if interval_time.seconds >= 20:
                    print('print_memory_full_info : interval_time = ' + str(interval_time))
                    f_csv.write(str(cur_tim) + ' ' + str(mem_info.rss) + ' ' + str(mem_info.vms) + ' ' + str(mem_info.shared) + ' ' + str(mem_info.text) + ' ' + str(mem_info.lib) + ' ' + \
                                str(mem_info.data) + ' ' + str(mem_info.dirty) + ' ' + str(mem_info.uss) + ' ' + str(mem_info.pss) + ' ' + str(mem_info.swap) + ' ' + msg + '\n')
                    print_memory_full_info.prv_tim = cur_tim

# def clc_elpsd_tim(bluetooth_server, data_type, prv_tim, msg):
#     cur_tim = datetime.datetime.now()
#     if list_of_variables_for_threads["run_measurement"]:
#         if list_of_variables_for_threads["is_measuring"]:
#             elpsd_tim = cur_tim - prv_tim
# #             bluetooth_server.write_data_only_to_storage(str(cur_tim) + ' ' + str(elpsd_tim.total_seconds() * 1000) + ' ' + msg, data_type)
#             asyncio.run(bluetooth_server.write_data_only_to_storage(str(cur_tim) + ' ' + str(elpsd_tim.total_seconds() * 1000) + ' ' + msg, data_type))
#     return cur_tim
