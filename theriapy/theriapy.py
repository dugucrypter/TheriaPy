import os
import shutil
import subprocess
import time
from datetime import datetime
from queue import Queue, Empty
from threading import Thread

from theriapy.regex import list_numbers_in_line, names_in_line, elts_in_header, RegExFinder


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    CBLACK = '\33[30m'


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


def get_output(out_queue):
    out_str = ''
    try:
        while True:  # Adds show_output from the Queue until it is empty
            out_str += out_queue.get_nowait()
    except Empty:
        return out_str


class Theriapy:
    """A class that opens Theriak as a subprocess, and parses the computed data.

    Attributes:
        therdom_dir : The directory path of the install Theriak-Domino programs
        working_dir : The working directory path
        db : The database used for calculations
        verbose : A boolean; if True, more details of the process are printed
        show_output : A boolean; if True, the output of the theriak.exe subprocess is printed
        wait_time : A float, the time-span waited before looking for the result of the calculation, in econds. Can be increased if calculations are tie-consuming
    """
    def __init__(self, therdom_dir, working_dir, db="JUN92d.bs", verbose=False, show_output=False, wait_time=0.2):
        os.environ['PATH'] = ''.join(
            [str(therdom_dir), ";", os.getenv('PATH'), ";", str(working_dir)
             ])
        self.verbose = verbose
        self.output = show_output
        self.working_dir = working_dir
        self.db = db
        self.wait_time = wait_time
        now = datetime.now()
        self.start_time = now.strftime("%Y_%m_%d_%H_%M_%S")
        self.save_dir = os.path.join(self.working_dir, self.start_time)
        os.mkdir(self.save_dir)
        self.step = 1
        print("TheriaPy initialized.")
        print("Working directory", working_dir, " --- Theriak-Domino directory :", therdom_dir, " --- Database :", db)

    def set_therin(self, compo, temperature, pressure):

        compo_str = ""
        comments = "     *Edited with TheriaPy " + str(self.start_time) + " step " + str(self.step)
        for key, val in compo.items():
            compo_str = compo_str + key + "(" + str(val) + ")"
        print("Step " + str(self.step) + " :", compo_str + " P " + str(pressure) + " T " + str(temperature))

        compo_str = "1  " + compo_str
        therin_path = os.path.join(self.working_dir, "THERIN")
        try:
            with open(therin_path, 'r') as file:
                lines = file.readlines()
        except IOError:
            msg = "Could not opent the file " + therin_path + "."
            print(msg)

        for i, line in enumerate(lines):
            if line[0] != '!':
                if i > 1:
                    lines[i] = "     " + str(temperature) + "     " + str(pressure) + "\n"
                    lines.insert(i + 1, compo_str + comments + "\n")
                    break

        try:
            with open(therin_path, 'w') as file:
                file.writelines(lines)
        except IOError:
            msg = "Could not opent the file " + therin_path + "."
            print(msg)

    def compute_step(self, comp, temperature, pressure):
        self.set_therin(comp, temperature, pressure)
        self.run_subprocess()
        parsed = self.parse_out()
        shutil.copyfile(os.path.join(self.working_dir, 'OUT'),
                        os.path.join(self.save_dir, 'OUT_' + 'step' + '_' + str(self.step)))
        if self.verbose:
            print("Saved in ", os.path.join(self.save_dir, 'OUT_' + 'step' + '_' + str(self.step)))
        self.step += 1
        return parsed

    def write(self, content):
        self.p.stdin.write(str(content) + "\n")
        self.p.stdin.flush()

    def show_output(self):
        output = get_output(self.out_queue)
        print(bcolors.OKBLUE, output, bcolors.CBLACK, )

    def run_subprocess(self):
        self.p = subprocess.Popen(['theriak'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  shell=False, universal_newlines=True, cwd=self.working_dir)

        self.out_queue = Queue()
        out_thread = Thread(target=enqueue_output, args=(self.p.stdout, self.out_queue))
        out_thread.daemon = True
        out_thread.start()

        # Db select
        if self.output:
            self.show_output()
        self.write(self.db)
        time.sleep(self.wait_time)

        # Type of calculation
        if self.output:
            self.show_output()
        self.write('no')
        time.sleep(self.wait_time)

        if self.output:
            self.show_output()

        # Close process
        self.p.kill()

    def jump_lines(self, file, step):
        for i in range(step):
            file.readline()

    def parse_out(self):
        data_vol_d = []
        data_h2o_compo = []
        data_compo = []

        out_path = os.path.join(self.working_dir, "OUT")
        try:
            with open(out_path, 'r') as file:
                line = file.readline()

                while line:
                    reg_match = RegExFinder(line)
                    if reg_match.volumes_densities:
                        data_vol_d = self.parse_vol_d(file)

                    if reg_match.h2o_content:
                        data_h2o_compo = self.parse_h2o_phases(file)

                    if reg_match.elements_in_phases:
                        data_compo = self.parse_compo(file)

                    line = file.readline()

        except IOError:
            msg = "Could not opent the file " + out_path + "."
            print(msg)

        return data_vol_d, data_h2o_compo, data_compo

    def parse_vol_d(self, file):

        data_vol_d = [["Phase", "N", "Volume/mol", "volume[ccm]", "vol%",
                       "wt/mol", "wt [g]", "wt [%]",
                       "density"], ]

        solids_checked = False
        gases_fluids_checked = False

        self.jump_lines(file, 4)

        while not solids_checked:
            line = file.readline()
            if 'exit THERIAK' in line:
                solids_checked = True
            else:
                # check lines
                match = names_in_line(line)
                if match and match.group(1) not in ("----------",):
                    if match.group(1) == "total":
                        lnbs = list_numbers_in_line(line)
                        phase_row = ["Total", '', '', lnbs[0], lnbs[1], '', lnbs[2], lnbs[3], lnbs[4]]
                        data_vol_d.append(phase_row)
                        solids_checked = True
                    else:
                        lnbs = list_numbers_in_line(line)
                        phase_row = [match.group(1), *lnbs]
                        data_vol_d.append(phase_row)

        self.jump_lines(file, 4)

        while not gases_fluids_checked:
            line = file.readline()
            if 'exit THERIAK' in line or '-------------' in line:
                gases_fluids_checked = True
            else:
                # check lines
                match = names_in_line(line)
                if match and match.group(1) not in ("----------",):
                    lnbs = list_numbers_in_line(line)
                    phase_row = [match.group(1), lnbs[0], lnbs[1], lnbs[2], '', lnbs[3], lnbs[4], '', lnbs[5]]
                    data_vol_d.append(phase_row)

        return data_vol_d

    def parse_h2o_phases(self, file):

        data_h2o_phases = [["Phase", "N", "H2O [pfu]", "H2O [mol]", "H2O [g]",
                            "wt% of phase", "wt% of solids", "wt% of H2O.solid", ], ]

        solids_checked = False
        gases_fluids_checked = False

        self.jump_lines(file, 2)
        line = file.readline()
        if "solid phases" in line :
            solids_checked = False
        elif "gases and fluids" in line :
            solids_checked = True
            self.jump_lines(file, 1)

        while not solids_checked:
            line = file.readline()
            if 'exit THERIAK' in line:
                solids_checked = True
            else:
                # check lines
                match = names_in_line(line)
                if match and match.group(1) not in ("----------", "--------"):
                    if match.group(1) == "total":
                        lnbs = list_numbers_in_line(line)
                        phase_row = ["Total (solids)", '', '', lnbs[0], lnbs[1], '', lnbs[2], '']
                        data_h2o_phases.append(phase_row)
                        solids_checked = True
                        self.jump_lines(file, 4)
                    else:
                        lnbs = list_numbers_in_line(line)
                        phase_row = [match.group(1), *lnbs]
                        data_h2o_phases.append(phase_row)


        while not gases_fluids_checked:
            line = file.readline()
            match = names_in_line(line)
            if match and match.group(1) not in ("----------",):
                lnbs = list_numbers_in_line(line)
                phase_row = [match.group(1), *lnbs, '', '']
                data_h2o_phases.append(phase_row)
            else:
                gases_fluids_checked = True

        return data_h2o_phases

    def parse_compo(self, file):

        data_compo = []
        checked = False
        nrow = 1  # For multilines rows
        self.jump_lines(file, 2)
        line = file.readline()

        elts = elts_in_header(line)
        if elts[-1] != 'E':
            line = file.readline()
            elts.extend(elts_in_header(line))
            nrow += 1
        elts_header = ['Phase', ]
        elts_header.extend(elts)
        data_compo.append(elts_header)

        while not checked:
            line = file.readline()
            if 'exit THERIAK' in line:
                checked = True
            else:
                # check lines
                match = names_in_line(line)
                if match and match.group(1) not in ("----------", "elements"):
                    if match.group(1) == "total:":
                        checked = True
                    k = 1
                    lnbs = []
                    while k <= nrow:
                        lnbs.extend(list_numbers_in_line(line))

                        if k < nrow:
                            line = file.readline()
                        k += 1
                    phase_row = [match.group(1), *lnbs]
                    data_compo.append(phase_row)

        return data_compo
