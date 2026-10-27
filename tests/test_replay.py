from bumpless.replay import paced, public_event, public_result


def test_paced_real_speed_and_capped_fast():
    evs = [{"ts": 0.0}, {"ts": 10.0}, {"ts": 10.5}]
    assert [d for d, _ in paced(evs, 1.0)] == [0.0, 10.0, 0.5]
    assert [d for d, _ in paced(evs, 4.0)] == [0.0, 1.5, 0.125]


def test_local_paths_are_scrubbed():
    r = public_result({"workspace": "C:/tmp/x", "source": r"C:\Users\me\repos\pydantic_app",
                       "output": {"patch": "C:/a.patch", "report": "C:/r.md", "branch": "b"}})
    assert r == {"source": "pydantic_app", "output": {"branch": "b"}}
    assert public_result({"source": "https://github.com/a/b"})["source"] == "https://github.com/a/b"
    ev = public_event({"id": 1, "ts": 0, "type": "progress",
                       "data": {"message": "m", "patch": "C:/a", "traceback": "Traceback..."}})
    assert ev["data"] == {"message": "m"}
