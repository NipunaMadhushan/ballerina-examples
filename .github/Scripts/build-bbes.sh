#!/bin/bash

BBE_DATA_FILE="$1"

bbes=()

for index in $(jq '. | keys | .[]' $BBE_DATA_FILE)
do
  samples=$(jq -r ".[$index].samples" $BBE_DATA_FILE)
  for bbe_url in $(jq -r ".[].url" <<< "$samples")
  do
    bbes[${#bbes[@]}]=$bbe_url
  done
done

echo "${bbes[56]}"
