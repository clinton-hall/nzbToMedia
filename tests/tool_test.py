import nzb2media.tool


def test_tool_in_path():
    ffmpeg = nzb2media.tool.in_path('ffmpeg')
    avprobe = nzb2media.tool.in_path('avprobe')
    assert ffmpeg or avprobe
