import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ipty  # noqa: E402

PLAIN = "-q -i"  # the plain Python REPL: no IPython needed for the test


def test_cells_are_typed_and_marker_found():
    text = ipty.run(sys.executable, ["x = 6*7", "print('ALIVE', x)"], repl=PLAIN, wait=1.0, start_wait=1.0)
    assert "ALIVE 42" in text


def test_a_crash_before_the_marker_means_no_marker():
    # the REPL dies on cell 1, so cell 2 never prints: absence of the marker is the failure signal
    text = ipty.run(sys.executable, ["import os; os._exit(3)", "print('ALIVE', 6*7)"],
                    repl=PLAIN, wait=1.0, start_wait=1.0)
    assert "ALIVE 42" not in text


def test_main_exit_codes():
    assert ipty.main(["--repl", PLAIN, "--wait", "1", "--marker", "OK7", "print('OK' + str(7))"]) == 0
    assert ipty.main(["--repl", PLAIN, "--wait", "1", "--marker", "NEVER", "print(1)"]) == 1
