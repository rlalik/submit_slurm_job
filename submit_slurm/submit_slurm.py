#!/usr/bin/env python3

"""
Documentation, License etc.

@package submit_slurm
"""

import os
import sys
import glob
import argparse
import shlex
import subprocess
from itertools import islice
from pathlib import Path
import shutil


def serialize_list(data_list: list):
    if isinstance(data_list, list):
        return ";".join(x for x in data_list)
    return data_list


def make_exports_string(exports_dict: dict):
    return ",".join([f"{k}={serialize_list(v)}" for k, v in exports_dict.items()])


def parse_args():
    def_time = 120
    def_mem = "1000mb"
    def_events = 1000000
    def_script = "job_script.sh"

    parser = argparse.ArgumentParser(description="Submit jobs to GSI batch farm")
    parser.add_argument("arguments", help="list of arguments", type=str, nargs="+")

    parser.add_argument("--partition", help="partition", type=str, default="main")

    parser.add_argument(
        "-e",
        "--events",
        help="number of events per file to be processed",
        type=int,
        default=def_events,
    )
    # resources
    parser.add_argument(
        "-t", "--time", help="time need to finish task", type=int, default=def_time
    )
    parser.add_argument(
        "-m", "--mem", help="requested memory", type=str, default=def_mem
    )

    # payload
    payload_group = parser.add_mutually_exclusive_group(required=True)

    payload_group.add_argument(
        "-p",
        "--payload",
        help="comma separated paylod to transfer to workdir",
        type=str,
        default=None,
    )
    payload_group.add_argument(
        "--payload-file",
        help="file containing paylod to transfer to workdir",
        type=str,
        default=None,
    )

    # files and locations
    parser.add_argument(
        "-s", "--script", help="execute script", type=str, default=def_script
    )
    parser.add_argument(
        "-d", "--directory", help="output directory", type=str, default="."
    )
    parser.add_argument("-w", "--workdir", help="workdir", type=str, required=True)
    parser.add_argument("--logdir", help="log directory", type=str, default="log")

    parser.add_argument(
        "-n",
        "--files",
        help="number of files you want to proceed",
        type=int,
        default=-1,
    )

    # job executions
    parser.add_argument(
        "-g", "--group", help="group inputs in larger groups", type=int, default=1
    )

    parser.add_argument(
        "-l", "--limit", help="limit jobs into max packages", type=int, default=0
    )

    inputs_group = parser.add_mutually_exclusive_group()
    inputs_group.add_argument(
        "-a", "--array", help="send as array job", nargs="?", default=None
    )
    inputs_group.add_argument(
        "-f", "--file", help="input is single file", action="store_true", default=False
    )

    # other
    parser.add_argument(
        "-v", "--verbose", help="verbose mode", action="store_true", default=False
    )
    parser.add_argument(
        "--pretend",
        help="pretend mode, do not send actuall jobs",
        action="store_true",
        default=False,
    )

    return parser.parse_args()


def build_slurm_command(
    args, job_script, exports_dict, log_file, resources=None, contianer=None
):
    return f'{array_args} -o {logfile} {resources} --export="{make_exports_string(exports_dict)}"'
    # command += " -- {:s} {:s}".format(
    # env["SINGULARITY_CONTAINER"], jobscript
    # )


def chunks(data: list, size: int):
    """Split data in size-large chunks as list of tuples."""
    it = iter(data)
    return tuple(iter(lambda: tuple(islice(it, size)), ()))


def split_list_into_jobs(inputs, size=1):
    """Open list files and convert into chunks."""
    with open(inputs) as inputs_file:
        all_lines = inputs_file.read().splitlines()

    return chunks(all_lines, size)


def create_jobs_array_from_chunks(
    job_array_file, inputs_chunks, separator=" ", extra_args={}
):
    """Create job array file from chunks. Can add extra arguments from dictionary."""
    with open(job_array_file, "w") as f:
        for chunk in inputs_chunks:
            f.write(separator.join(chunk) + " ")

            for k, v in extra_args.items():
                f.write(f"{k} {v}")

            f.write("\n")


def make_job_params(inputs, events, odir):
    return {"input": inputs, "events": events, "odir": odir}


def transfer_payload_list(payload_list: tuple, workdir: str):
    for p in payload_list:
        if os.path.isdir(p):
            shutil.copytree(p, workdir, dirs_exist_ok=True)
        else:
            shutil.copy2(p, workdir)


def transfer_payload_from_string(payload: str):
    return [p.strip() for p in payload.split(",")]


def transfer_payload_from_file(payload_file: str):
    paylod_from_file = []
    with open(payload_file) as f:
        for payload in f:
            _payload = payload.strip()
            if os.path.exists(_payload):
                paylod_from_file.append(_payload)
    return paylod_from_file


if __name__ == "__main__":
    args = parse_args()

    if args.verbose:
        print(args)

    submissiondir = os.getcwd() + "/"
    tpl_resources = "--time={0:1d}:{1:02d}:00 --mem-per-cpu={2:s} -p main"
    jobscript = submissiondir + args.script

    env = {}
    env.update(os.environ)

    i = 0

    resources = tpl_resources.format(int(args.time / 60), args.time % 60, args.mem)
    lines = []

    events = args.events

    deps = [None] * args.limit

    payload_list = []

    if args.payload_file:
        payload_list = payload_list + transfer_payload_from_file(args.payload_file)
    if args.payload:
        payload_list = payload_list + transfer_payload_from_string(args.payload)

    payload_list.append(args.script)

    payload_set = set(payload_list)

    if not args.pretend:
        transfer_payload_list(payload_set, args.workdir)

    print(f"Main payload list : {' '.join(payload_set)}")

    for arg in args.arguments:
        if args.file is False:
            lines = split_list_into_jobs(arg, args.group)
        else:
            lines = (arg,)

        num_lines = len(lines)

        # print("Line=", lines, num_lines)

        jobid_list = ""

        array_arg = ""
        if args.array is None:
            array_args = "--array=0-{:d}".format(num_lines - 1)
        elif args.array[0] == "%":
            array_args = "--array=0-{:d}{:s}".format(num_lines - 1, args.array)
        else:
            array_args = "--array={:s}".format(args.array)

        job_file_name = "job_array__" + arg.replace("/", "__")

        paylod_list = []

        remote_job_array = os.path.abspath(args.workdir + "/" + job_file_name)
        exports = make_job_params(remote_job_array, args.events, args.directory)

        remote_logdir = args.workdir + "/" + args.logdir + "/"
        remote_logfile = remote_logdir + "slurm-%A_%a-array.log"

        command = (
            '--chdir {:s} {:s} -J {:s} -o {:s} {:s} --export="{:s}" -- {:s}'.format(
                args.workdir,
                array_args,
                Path(arg).stem,
                remote_logfile,
                resources,
                make_exports_string(exports),
                jobscript,
            )
        )

        job_command = "sbatch " + command
        status = "-- PRETEND MODE --"

        if not args.pretend:
            create_jobs_array_from_chunks(job_file_name, lines)
            paylod_list = paylod_list + transfer_payload_from_string(job_file_name)

            if not os.path.isdir(remote_logdir):
                os.makedirs(remote_logdir)

            if os.path.isfile(remote_logfile):
                os.remove(remote_logfile)

            payload_set = set(paylod_list)
            transfer_payload_list(payload_set, args.workdir)

            proc = subprocess.Popen(
                shlex.split(job_command),
                stdout=subprocess.PIPE,
                shell=False,
                env=env,
            )
            (out, err) = proc.communicate()

            if out[0:19] == b"Submitted batch job":
                status = out[20:-1].decode()
            else:
                status = f"Job failed with error: {err}"

        print(f"- Input file      : {arg}")
        print(f"  Job array file  : {job_file_name} -> {remote_job_array}")
        print(f"  Array info      : {array_args}")
        print(f"  Exports         : {make_exports_string(exports)}")
        print(f"  Job command     : {job_command}")
        print(f"  Submit status   : {status}")
        # print(f"  Payload list    : {' '.join(payload_set)}")

        #         if args.limit > 0 and deps[i % args.limit] != None:
        #             command += " -d afterany:" + deps[i % args.limit]
        #         command += " -- {:s} {:s}".format(
        #             env["SINGULARITY_CONTAINER"], jobscript
        #         )

        #     print(i, " entries submitted")
