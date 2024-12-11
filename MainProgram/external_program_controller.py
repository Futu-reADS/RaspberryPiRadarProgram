import subprocess
import threading
import time
import queue
import numpy as np
import os

class ExternalProgramController:
    def __init__(self, program_path):
        self.program_path = program_path
        self.process = None
        self.thread = None
        self.output_queue = queue.Queue()
        
    def start_program(self):
        self.process = subprocess.Popen(
                            [self.program_path],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            text=True
                        )
#         print(" /// external c program probably start. /// ")  # for debug
        self.thread = threading.Thread(target=self.read_output)
        self.thread.start()
#         print(" /// read_output thread starts. /// ")  # for debug
        
    def read_output(self):
        while True:
            output = self.process.stdout.readline()
            if output == '' and self.process.poll() is not None:
                break
            if output:
#                 print(f"External program output: {output.strip()}")
                if output[0] == '(':
                    output = output.strip('\n')
                    output = output.replace('\n', '')
                    iq_data_str_list = output.split('\t')
                    del iq_data_str_list[-1]
#                     print(f"length of iq_data_str_list = {len(iq_data_str_list)}")  # for debug
                    iq_data = [self.str_to_complex128(iq_data_str) for iq_data_str in iq_data_str_list]
                    iq_array = np.array(iq_data).reshape(1, -1)
#                     print(' /// read_output()@ExtrnlPrgrmCntrllr type of iq_array : ' + str(type(iq_array)) + ' /// ')  # for debug
#                     print(' /// read_output()@ExtrnlPrgrmCntrllr shape of iq_array : ' + str(iq_array.shape) + ' /// ')  # for debug
                    self.output_queue.put(iq_array)
                else:
                    continue

    def str_to_complex128(self, s):
#         real, imag = map(float, s.strip('()').split(','))
        real, imag = map(int, s.strip('()').split(','))
        return np.complex128(complex(real, imag))

    def send_command(self, command):
        try:
            if self.process and self.process.poll() is None:
                self.process.stdin.write(f"{command}\n")
                self.process.stdin.flush()
            else:
                print("External program is not running.")
        except BrokenPipeError:
            print("Broken pipe error occurred. External program might have terminated.")

    def get_output(self):
        output_list = []
        while not self.output_queue.empty():
            output_list.append(self.output_queue.get())
#             print(' /// get_output()@ExtrnlPrgrmCntrllr type of output_list[-1] : ' + str(type(output_list[-1])) + ' /// ')  # for debug
#             if type(output_list[-1]) is np.ndarray:
#                 print(' /// get_output()@ExtrnlPrgrmCntrllr shape of output_list[-1] : ' + str(output_list[-1].shape) + ' /// ')  # for debug
        return output_list

    def stop_program(self):
        if self.process:
            self.send_command('q')
            self.thread.join()
            self.process.terminate()
            self.process.wait()

if __name__ == "__main__":
    controller = ExternalProgramController(os.getenv('EXTERNAL_PROGRAM_FILE_PATH'))
    controller.start_program()
    
    try:
        while True:
            command = input("Enter the command (g: get data, q: quit): ")
            if command == 'q':
                break
            elif command == 'g':
                controller.send_command(command)
#                 time.sleep(1)  # Wait a moment and get the output
                time.sleep(0.02)  # Wait a moment and get the output
                output = controller.get_output()
                if output:
                    print(' /// @main length of output : ' + str(len(output)) + ' /// ')  # for debug
                    for element in output:
                        print(' /// @main type of element : ' + str(type(element)) + ' /// ')  # for debug
                        if type(element) is np.ndarray:
                            print(' /// @main shape of element : ' + str(element.shape) + ' /// ')  # for debug
                            print(element[0][0])
                            print(element[0][-1])
            else:
                print('Invalid commad')
    finally:
        controller.stop_program()
        print('The program has ended.')
