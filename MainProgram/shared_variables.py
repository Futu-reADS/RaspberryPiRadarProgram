import datetime

list_of_variables_for_threads = {}

def clc_elpsd_tim(f_csv, prv_tim, msg):
    cur_tim = datetime.datetime.now()
    if list_of_variables_for_threads["run_measurement"]:
        if list_of_variables_for_threads["is_measuring"]:
            if not f_csv.closed:
                elpsd_tim = cur_tim - prv_tim
                f_csv.write(str(cur_tim) + ' ' + str(elpsd_tim.total_seconds() * 1000) + ' ' + msg + '\n')
    return cur_tim
