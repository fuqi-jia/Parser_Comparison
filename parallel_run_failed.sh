#!/bin/bash

for i in {1..117}
do
    nohup ./run_failed.sh failed_files_s/part$i > results_failed/failed_files_part$i.log 2>&1 &
done

