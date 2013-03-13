#!/bin/sh 

git clone git://github.com/FFmpeg/FFmpeg.git

cd FFmpeg

./configure --enable-gpl --enable-version3 --disable-w32threads --enable-bzlib --enable-frei0r --enable-gnutls --enable-libass --enable-libbluray --enable-libcaca --enable-libfreetype --enable-libgsm --enable-libilbc --enable-libmp3lame --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libschroedinger --enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame --enable-libvo-aacenc --enable-libvo-amrwbenc --enable-libvorbis --enable-libvpx --enable-libx264 --enable-libxavs --enable-libxvid --enable-zlib

make

make install
