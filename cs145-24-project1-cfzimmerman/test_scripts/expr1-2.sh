#!/bin/bash

echo "run two-core controller for FatTree"
./controller/controller_fattree_twocore.py 4
echo "generate trace"
./apps/trace/generate_trace.py ./apps/trace/project1.json

for i in {1..5}
do
    echo "run traffic traces $i/5"
    sudo ./apps/send_traffic.py --trace ./apps/trace/project1.trace
done
echo "finish Expr 1-2"
