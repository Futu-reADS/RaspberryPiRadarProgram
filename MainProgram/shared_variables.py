import datetime
import psutil
# import asyncio
import pandas as pd

list_of_variables_for_threads = {}

def clc_elpsd_tim(f_csv, prv_tim, msg):
    cur_tim = datetime.datetime.now()
    if list_of_variables_for_threads["run_measurement"]:
        if list_of_variables_for_threads["is_measuring"]:
            if not f_csv.closed:
                elpsd_tim = cur_tim - prv_tim
                f_csv.write(str(cur_tim) + ' ' + str(elpsd_tim.total_seconds() * 1000) + ' ' + msg + '\n')
    return cur_tim

# def print_memory_full_info(f_csv, msg):
def print_memory_full_info(bluetooth_server, f_csv, msg):
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
                    df_hr_mem_usg = bluetooth_server.df_hr.memory_usage(deep=True).sum()
                    df_rr_mem_usg = bluetooth_server.df_rr.memory_usage(deep=True).sum()
                    df_rtb_mem_usg = bluetooth_server.df_rtb.memory_usage(deep=True).sum()
                    df_raw_mem_usg = bluetooth_server.df_raw.memory_usage(deep=True).sum()
                    df_bp_mem_usg = bluetooth_server.df_bp.memory_usage(deep=True).sum()
                    df_bpint_mem_usg = bluetooth_server.df_bpint.memory_usage(deep=True).sum()
                    df_hea3_mem_usg = bluetooth_server.df_hea3.memory_usage(deep=True).sum()
                    df_hea9_mem_usg = bluetooth_server.df_hea9.memory_usage(deep=True).sum()
                    df_hea10_mem_usg = bluetooth_server.df_hea10.memory_usage(deep=True).sum()
                    df_hea11_mem_usg = bluetooth_server.df_hea11.memory_usage(deep=True).sum()
                    df_hea6_mem_usg = bluetooth_server.df_hea6.memory_usage(deep=True).sum()
                    df_sch_mem_usg = bluetooth_server.df_sch.memory_usage(deep=True).sum()
                    df_total_mem_usg = df_hr_mem_usg + df_rr_mem_usg + df_rtb_mem_usg + df_raw_mem_usg + df_bp_mem_usg + df_bpint_mem_usg + \
                                       df_hea3_mem_usg + df_hea9_mem_usg + df_hea10_mem_usg + df_hea11_mem_usg + df_hea6_mem_usg + df_sch_mem_usg
                    f_csv.write(str(cur_tim) + ' ' + str(df_hr_mem_usg) + ' ' + str(df_rr_mem_usg) + ' ' + str(df_rtb_mem_usg) + ' ' + str(df_raw_mem_usg) + ' ' + \
                                str(df_bp_mem_usg) + ' ' + str(df_bpint_mem_usg) + ' ' + \
                                str(df_hea3_mem_usg) + ' ' + str(df_hea9_mem_usg) + ' ' + str(df_hea10_mem_usg) + ' ' + str(df_hea11_mem_usg) + ' ' + str(df_hea6_mem_usg) + ' ' + \
                                str(df_sch_mem_usg) + ' ' + str(df_total_mem_usg) + ' ' + \
                                str(mem_info.rss) + ' ' + str(mem_info.vms) + ' ' + str(mem_info.shared) + ' ' + str(mem_info.text) + ' ' + str(mem_info.lib) + ' ' + \
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
