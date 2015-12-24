#!/bin/bash

set -x

install_file=$1
tar_file=${install_file##*/}
final_file=${tar_file%%.*}
wget $install_file
tar zxf $tar_file

echo Done