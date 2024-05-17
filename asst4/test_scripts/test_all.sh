#!/bin/bash

for num in {0..5}; do
	rm -f output.txt
	echo "test_base $num"
	if ! bash test_base.sh; then
		exit 1
	fi
done

for num in {0..5}; do
	rm -f output.txt
	echo "test_opt $num"
	if ! bash test.sh; then
		exit 1
	fi
done
