from .context import submit_slurm

import pytest


def test_make_exports_string():
    with pytest.raises(AttributeError):
        res = submit_slurm.make_exports_string([1, 2, 3])

    assert (
        submit_slurm.make_exports_string({"key1": "val1", "key2": "val2"})
        == "key1=val1,key2=val2"
    )

    assert (
        submit_slurm.make_exports_string({"key1": "val1", "key2": ["val2a", "val2b"]})
        == "key1=val1,key2=val2a;val2b"
    )


def test_chunks():
    l1 = [1, 2, 3, 4, 5, 6]

    assert submit_slurm.chunks(l1, 1) == ((1,), (2,), (3,), (4,), (5,), (6,))
    assert submit_slurm.chunks(l1, 2) == (
        (1, 2),
        (3, 4),
        (5, 6),
    )
    assert submit_slurm.chunks(l1, 3) == (
        (1, 2, 3),
        (4, 5, 6),
    )
    assert submit_slurm.chunks(l1, 4) == (
        (1, 2, 3, 4),
        (5, 6),
    )
    assert submit_slurm.chunks(l1, 5) == (
        (1, 2, 3, 4, 5),
        (6,),
    )
    assert submit_slurm.chunks(l1, 6) == ((1, 2, 3, 4, 5, 6),)


def test_split_list_into_jobs():
    assert list(submit_slurm.split_list_into_jobs("test/test_data.txt", 3)) == [
        ("line1", "line2", "line3"),
        ("line4", "line5", "line6"),
    ]


def test_create_jobs_array_from_chunks():
    submit_slurm.create_jobs_array_from_chunks(
        "test_job_array.txt", submit_slurm.split_list_into_jobs("test/test_data.txt", 3)
    )


def test_export_string():
    assert (
        submit_slurm.make_exports_string(
            submit_slurm.make_job_params("key1", 1000, "key2")
        )
        == "input=key1,events=1000,odir=key2"
    )
