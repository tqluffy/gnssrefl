from pathlib import Path

from gnssrefl.extract_arcs import _get_arc_filename, move_arc_to_failqc


def _arc_meta():
    return {
        'sat': 5,
        'freq': 1,
        'az_min_ele': 123.4,
        'arc_timestamp': 10.5,
    }


def test_move_arc_to_failqc_txt(refl_code_with_mchl):
    meta = _arc_meta()
    station, year, doy = 'mchl', 2025, 11

    sdir = refl_code_with_mchl / str(year) / 'arcs' / station / f'{doy:03d}'
    fail_dir = sdir / 'failQC'
    fail_dir.mkdir(parents=True, exist_ok=True)

    txt_path = Path(_get_arc_filename(str(sdir) + '/', meta['sat'], meta['freq'],
                                      meta['az_min_ele'], meta['arc_timestamp']))
    txt_path.write_text('dummy arc')

    move_arc_to_failqc(meta, station, year, doy)

    moved_txt = Path(_get_arc_filename(str(fail_dir) + '/', meta['sat'], meta['freq'],
                                       meta['az_min_ele'], meta['arc_timestamp']))
    assert not txt_path.exists()
    assert moved_txt.exists()


def test_move_arc_to_failqc_pickle(refl_code_with_mchl):
    meta = _arc_meta()
    station, year, doy = 'mchl', 2025, 12

    sdir = refl_code_with_mchl / str(year) / 'arcs' / station / f'{doy:03d}'
    fail_dir = sdir / 'failQC'
    fail_dir.mkdir(parents=True, exist_ok=True)

    txt_name = _get_arc_filename(str(sdir) + '/', meta['sat'], meta['freq'],
                                 meta['az_min_ele'], meta['arc_timestamp'])
    pickle_path = Path(txt_name[:-4] + '.pickle')
    pickle_path.write_bytes(b'pickle arc')

    move_arc_to_failqc(meta, station, year, doy)

    moved_pickle = Path(_get_arc_filename(str(fail_dir) + '/', meta['sat'], meta['freq'],
                                          meta['az_min_ele'], meta['arc_timestamp'])[:-4] + '.pickle')
    assert not pickle_path.exists()
    assert moved_pickle.exists()
