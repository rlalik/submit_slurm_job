Helper script so send slurm computing jobs.

## Example


We want to run the job in some `workdir` located on cluster storage, let's say `/lustre/user/foo/job1`.

In our `currentdir` we have our `job_script.sh`, `my_fancy_exec_to_run_on_farm` and extra `exec_param_file.txt` which is required to run `my_fancy_exec_to_run_on_farm`. Also, `my_fancy_exec_to_run_on_farm` takes as input an extra argument. We have list of hundereds of a such arguments in a `inputs.txt`. Our `currentdir` looks following:
```text
$ tree
.
├── exec_param_file.txt
├── inputs.txt
├── job_script.sh
└── my_fancy_exec_to_run_on_farm
```

### A job script

An example `job_script.sh` which will be executed on the farm:
```bash
#!/bin/bash

# print some extra node info
date
hostname

echo "inputs:"
echo " input=$input"
echo " events=$events"
echo " odir=$odir"

# detect if the array mode, and then take line from the job array file
if [[ -n ${SLURM_ARRAY_TASK_ID} ]]; then
    echo "ARRAY: ${SLURM_ARRAY_TASK_ID} in ${input}"
    line=$(sed -n $((${SLURM_ARRAY_TASK_ID}+1))p ${input})
    IFS=' ' read -ra linearr <<< "$line"
    file=${linearr[0]}
    sodir=${linearr[1]}
else
    echo "NO ARRAY"
    file=$input
fi

# create output directory for the job
mkdir -p $odir

time ./my_fancy_exec_to_run_on_farm -p exec_param_file.txt $file $events
```

### A inputs list
File with line-separated list of independent sets of arguments for our exec.
```
data1
data2
data3
...
```

### Job submission
We would like to submit the job in a following way:
```bash
submit_slurm.py inputs.txt -w /lustre/user/foo/job1 -p my_fancy_exec_to_run_on_farm,exec_param_file.txt -d results
```
where:
* `inputs.txt` - list of independent inputs
* `-w ___` - work dir, where the slurm job will be run
* `-p ___,___,...` is the payload - files which should be copied to the `workdir`
* `-d ____` - directory for output of our job

The `workdir` will looks as follow:
```text
/lustre/user/foo.job1 $ tree
.
├── exec_param_file.txt
├── job_array__inputs.txt
├── job_script.sh
├── log
│   ├── slurm-8931_0-array.log
│   ├── slurm-8931_1-array.log
│   └── ...
├── my_fancy_exec_to_run_on_farm
└── results
    ├── data1.out
    ├── data2.out
    └── ...
```
#### Job array
The submit scripts takes the inputs and converts them into job array file. The job array file is then transferred to the `workdir`. The job array file is constructed of the prefix `job_array__` and the input file. If the input files path contains directories, the `/` is converted to `__`, e.g. for `inputs/input_case_a.txt` the job array file will be `job_array__inputs__input_case_a.txt`.

If you executable can take more than one input data and one wants to merge several inputs into one job, one can use grouping option `-g [n]` which will merge multiple inputs into job array. E.g. for input like:
```text
data1
data2
data3
data4
data5
data6
```
the group option `-g 2` will produce job array
```text
data1 data2
data3 data4
data5 data6
```

#### Payload

Payload is a list of files to be transferred. Beside explicitly specified files also the job script file and the job array file are transferred. The payload may be specified also in the form of a list of files and directories to be specified, in our case it could be:
```bash
$ cat payload.txt
my_fancy_exec_to_run_on_farm
exec_param_file.txt
```
and transferred with
We would like to submit the job in a following way:
```bash
submit_slurm.py inputs.txt -w /lustre/user/foo/job1 --payload-file payload.txt -d results
```

# Installation

Use pip, e.g. (use `--user` for no system-wide installations):
```bash
git clone https://github.com/rlalik/submit_slurm_job
cd submit_slurm_job
# for system wide
python -m pip install .
# for local installation only
python -m pip install . --user--break-system-packages
```
