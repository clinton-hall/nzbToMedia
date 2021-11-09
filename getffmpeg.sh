#!/bin/sh

# get ffmpeg/yasm/x264
git clone git://source.ffmpeg.org/ffmpeg.git FFmpeg
git clone git://github.com/yasm/yasm.git FFmpeg/yasm
git clone https://code.videolan.org/videolan/x264.git FFmpeg/x264

# compile/install yasm
cd FFmpeg/yasm
./autogen.sh
./configure
make
make install
cd -

# compile/install x264
cd FFmpeg/x264
./configure --enable-static --enable-shared
make
make install
ldconfig
cd -

# compile/install ffmpeg
cd FFmpeg
./configure --disable-asm --enable-libx264 --enable-gpl
make install
cd -
