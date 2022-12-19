import nzb2media


def test_has_ffmpeg():
    nzb2media.configure_utility_locations()
    assert nzb2media.FFMPEG is not None
    assert nzb2media.FFMPEG.exists()
