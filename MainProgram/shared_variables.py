import datetime
import psutil
import os
import subprocess

list_of_variables_for_threads = {}

def clc_elpsd_tim(f_csv, prv_tim, msg):
    cur_tim = datetime.datetime.now()
    if list_of_variables_for_threads["run_measurement"]:
        if list_of_variables_for_threads["is_measuring"]:
            if not f_csv.closed:
                elpsd_tim = cur_tim - prv_tim
                f_csv.write(str(cur_tim) + ' ' + str(elpsd_tim.total_seconds() * 1000) + ' ' + msg + '\n')
    return cur_tim

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

def save_error_messages_to_a_log_file(type_of_info, comments):
    timestamp = datetime.datetime.now()
    date_time = timestamp.strftime('%Y%m%d_%H%M%S')
    st_dt_tm = date_time.split('_')

    filepath = '/home/futu-re/err_log/'
    filename_err_csv = 'log_err_' + st_dt_tm[0] + '.csv'
    if not os.path.exists(filepath + filename_err_csv):
        f_err_csv = open(filepath + filename_err_csv, 'w')
        if not f_err_csv.closed:
            f_err_csv.write('date,time,type of info,comments\n')
    else:
        f_err_csv = open(filepath + filename_err_csv, 'a')

    if not f_err_csv.closed:
        f_err_csv.write(st_dt_tm[0] + ',' + st_dt_tm[1] + ',' + type_of_info + ',' + comments + '\n')

    f_err_csv.close()

def get_mount_point_excluding_sda():
    # Run the df command and get the output
    result = subprocess.run(['df'], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')

    # Split the output into lines
    lines = output.split('\n')

    # Check each line for a device mount point that starts with /dev/sd and is not /dev/sda
    for line in lines:
        if line.startswith('/dev/sd') and not line.startswith('/dev/sda'):
            # Split the line into columns and return the mount point (the last column)
            columns = line.split()
            return columns[-1] + '/'

    return None
