import pathlib
from functools import cache
import json


@cache
def get_msb_meta(dataset_dir: pathlib.Path) -> dict[str, dict]:
    meta = {}
    for dataset_file in dataset_dir.rglob("*.jsonl"):
        with open(dataset_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                meta[data["instance_id"]] = data
                meta[data["instance_id"]]["language"] = dataset_file.parent.name
                meta[data["instance_id"]]["dataset_id"] = dataset_dir.name.lower()
    return meta


def get_instance_meta(dataset_dir: pathlib.Path, instance_id: str) -> dict:
    meta = get_msb_meta(dataset_dir)
    return meta[instance_id]


if __name__ == "__main__":
    print(
        get_instance_meta(
            pathlib.Path(".cache/multi_swe_bench/multi_swe_bench"),
            "rayon-rs__rayon-863",
        ).keys()
    )
