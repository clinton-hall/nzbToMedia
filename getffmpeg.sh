#!/bin/sh 

git clone https://github.com/FFmpeg/FFmpeg.git

cd FFmpeg

./configure --disable-yasm

make

make install
