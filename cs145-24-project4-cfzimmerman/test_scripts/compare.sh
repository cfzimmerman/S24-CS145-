#!/bin/bash
function compare {
	if diff -q $1 $2 >/dev/null; then
		printf "\nSUCCESS: Message received matches message sent!\n"
		printf "\n"
		exit 0
	else
		printf "\nFAILURE: Message received doesn't match message sent.\n"
		printf "\n"
		exit 1
	fi
}

compare $1 $2
