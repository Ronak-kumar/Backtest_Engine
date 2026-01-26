import subprocess
import sys
import pandas as pd
from glob import glob
import os
import time
import copy
import shutil
import psutil
from pathlib import Path

MAIN_DIR = Path(__file__).resolve().parent.parent

# is linux os.name is posix , for windows it is 'nt'

if os.name == 'posix':
    file_name = sys.argv[1][1:-1]
    max_terminals = int(sys.argv[2][:-1])

    venv_python = sys.executable
    print("Using Python interpreter:", venv_python)


    def subprocess_trigger(directory, script_name, argument):
        command = f"gnome-terminal -- bash -c 'cd {directory} && {venv_python} {script_name}.py {argument} && exit; exec bash'"
        process = subprocess.Popen(command, shell=True)


    strategy_path = f"{os.path.dirname(os.path.dirname(os.getcwd()))}/strategies/{file_name}/*.csv"
    # reading files from stratergy path

    all_files = pd.DataFrame(glob(strategy_path), columns=['location'])
    all_files['file_name'] = all_files['location'].apply(lambda x: x.split('/')[-1])
    all_files.set_index("file_name", inplace=True)
    all_files = all_files[all_files["location"].str.contains("csv")]

    saved_file = f"{os.path.dirname(os.path.dirname(os.getcwd()))}/backtest_results"
    terminals_open = 0
    i = 0
    terminal_process = os.path.join(os.path.dirname(os.getcwd()), "running_terminals")
    if os.path.exists(terminal_process):
        shutil.rmtree(terminal_process)
    os.makedirs(terminal_process, exist_ok=True)

    while i < len(all_files):
        print(f"File Running:-  {i + 1}/{len(all_files)}")
        chunk = all_files.iloc[[i]]
        for file, location in chunk.iterrows():
            df = pd.read_csv(location.item(), header=None)
            df.set_index(0, inplace=True)

            strategy = df.loc['strategy_name'].item()
            atr = df.loc['strategy_name'].item()

            waiting = 0
            time.sleep(0.5)
            print(f"directory name : {os.path.dirname(os.path.dirname(os.getcwd()))}")
            process = subprocess_trigger(directory=os.path.dirname(os.getcwd()), script_name='main_engine2_V37_db',
                                         argument=location.item())

            main_path = location.item().split(".")[0].split("/")[-1]
            temp_file = f"{terminal_process}/terminal_running_{main_path}.txt"
            f = open(temp_file, "w")
            f.write("0")
            f.close()
            subprocess_terminals = glob(f"{terminal_process}/*.txt")

            terminals_open += 1
            print("no of terminals open", terminals_open)

        while len(subprocess_terminals) >= max_terminals:
            subprocess_terminals = glob(f"{terminal_process}/*.txt")

        i = i + 1

if os.name == 'nt':
    file_name = sys.argv[1][2:-7]
    # file_name = "normal_straddle_nosl"

    venv_python = sys.executable
    print("Using Python interpreter:", venv_python)

    strategy_path = f"{MAIN_DIR}/strategies/{file_name}/*"

    all_files = pd.DataFrame(glob(strategy_path), columns=['location'])
    all_files['file_name'] = all_files['location'].apply(lambda x: x.split('\\')[-1])
    all_files.set_index("file_name", inplace=True)
    all_files = all_files[all_files["location"].str.contains("csv")]

    script_name=f"{MAIN_DIR}/Engines/Main_Engine"

    for file, location in all_files.iterrows():
        print(file)
        print(location.item())
        subprocess.call(f'start/min "" {venv_python} {script_name}.py {location.item()}', shell=True,
                        cwd=os.path.dirname(os.getcwd()))


    def kill_parent_process():
        try:
            current_process = psutil.Process(os.getpid())
            parent_process = current_process.parent()
            parent_process.terminate()  # or parent_process.kill() for forceful termination
            parent_process.wait(timeout=3)  # Wait for the parent process to terminate
            print(f"Parent process {parent_process.pid} terminated.")
        except psutil.NoSuchProcess:
            print("No parent process found.")
        except psutil.AccessDenied:
            print("Permission denied to terminate the parent process.")
        except psutil.TimeoutExpired:
            print("Timeout expired while waiting for the parent process to terminate.")


    time.sleep(4)
    kill_parent_process()
