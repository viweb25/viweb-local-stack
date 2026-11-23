"""Train an Ultralytics detector from an exported local YOLO dataset."""

import argparse
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml


def local_path(root: Path, parent: Path, value: str) -> Path:
    candidate = (parent / value).resolve()
    if not candidate.is_relative_to(root) or not candidate.exists():
        raise ValueError(f"Dataset path must exist inside the export: {value}")
    return candidate


def dataset_config(file: Path) -> dict:
    root = file.parent
    source = yaml.safe_load(file.read_text())
    if not isinstance(source, dict) or not isinstance(source.get("names"), (dict, list)):
        raise ValueError("data.yaml must define the YOLO class names.")
    if not source["names"]:
        raise ValueError("data.yaml needs at least one class name.")

    parent = local_path(root, root, str(source.get("path") or "."))
    result = {"path": str(parent), "names": source["names"]}
    for split in ("train", "val", "test"):
        value = source.get(split)
        if not value and split == "test":
            continue
        values = [value] if isinstance(value, str) else value
        if (
            not isinstance(values, list)
            or not values
            or not all(isinstance(item, str) and item for item in values)
        ):
            raise ValueError(f"data.yaml needs a valid {split} image path.")
        directories = [local_path(root, parent, item) for item in values]
        if not all(path.is_dir() for path in directories):
            raise ValueError(f"Use image directories for {split} in data.yaml.")
        relative = [str(path.relative_to(parent)) for path in directories]
        result[split] = relative[0] if isinstance(value, str) else relative
    return result


def main():
    from ultralytics import YOLO

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("/dataset/data.yaml"))
    parser.add_argument("--runs", type=Path, default=Path("/runs"))
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument(
        "--from-scratch",
        action="store_true",
        help="Initialize YOLO11n without pretrained weights.",
    )
    args = parser.parse_args()
    try:
        config = dataset_config(args.data.resolve())
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))

    # Ultralytics ships optional integrations. Keep inspection data on this machine.
    os.environ["WANDB_MODE"] = "disabled"
    from ultralytics import settings

    settings.update({"sync": False, "wandb": False, "mlflow": False, "comet": False})
    with TemporaryDirectory() as directory:
        manifest = Path(directory) / "data.yaml"
        manifest.write_text(yaml.safe_dump(config))
        model = YOLO("yolo11n.yaml" if args.from_scratch else "yolo11n.pt")
        model.train(
            data=str(manifest),
            project=str(args.runs),
            name="object-detection-scratch" if args.from_scratch else "object-detection",
            pretrained=not args.from_scratch,
            epochs=args.epochs,
            imgsz=args.imgsz,
            device=args.device,
            batch=args.batch,
            workers=0,
            plots=True,
        )
        run = Path(model.trainer.save_dir)
        checkpoint = run / "weights" / "best.pt"
        if not checkpoint.is_file():
            raise RuntimeError("Training completed without producing best.pt")
        if "test" in config:
            YOLO(str(checkpoint)).val(
                data=str(manifest),
                split="test",
                device=args.device,
                project=str(run),
                name="held-out-test",
                plots=True,
            )
        print(f"Training results: {run / 'results.csv'}")
        print(f"Candidate model: {checkpoint}")


if __name__ == "__main__":
    main()
