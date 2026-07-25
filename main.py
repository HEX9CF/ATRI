from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter

from PIL import Image, UnidentifiedImageError


@dataclass
class ProcessStats:
    total: int = 0
    processed: int = 0
    success: int = 0
    failed: int = 0
    unknown_date: int = 0


def main() -> None:
    args = parse_args()
    classify_files(args.input_dir, args.output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按图片 EXIF 拍摄日期复制文件到日期目录")
    parser.add_argument("input_dir", nargs="?", default="input", help="输入目录，默认 input")
    parser.add_argument("output_dir", nargs="?", default="output", help="输出目录，默认 output")
    return parser.parse_args()


def classify_files(input_dir: str, output_dir: str) -> None:
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.is_dir():
        raise NotADirectoryError(f"input path is not a directory: {input_path}")

    output_path.mkdir(parents=True, exist_ok=True)

    files = [file_path for file_path in input_path.rglob("*") if file_path.is_file()]
    stats = ProcessStats(total=len(files))

    start_at = perf_counter()
    print(f"[START] input={input_path} output={output_path}")
    print(f"[INFO] 待处理文件总数: {stats.total}")

    if not files:
        print_summary(stats, perf_counter() - start_at)
        return

    for index, file_path in enumerate(files, start=1):
        try:
            date_code = get_photo_date_code(file_path)
            if date_code == "000000":
                stats.unknown_date += 1

            target_dir = output_path / date_code
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = unique_target_path(target_dir, file_path.name)
            copy_file(file_path, target_path)

            stats.success += 1
            print(
                f"[{index}/{stats.total}] OK  {file_path} -> {target_path} "
                f"({index / stats.total:.1%})"
            )
        except Exception as exc:
            stats.failed += 1
            print(
                f"[{index}/{stats.total}] FAIL {file_path} "
                f"error={type(exc).__name__}: {exc} ({index / stats.total:.1%})"
            )
        finally:
            stats.processed += 1

    elapsed = perf_counter() - start_at
    print_summary(stats, elapsed)


def print_summary(stats: ProcessStats, elapsed_seconds: float) -> None:
    print("\n[SUMMARY] 处理完成")
    print(f"[SUMMARY] 总数: {stats.total}")
    print(f"[SUMMARY] 已处理: {stats.processed}")
    print(f"[SUMMARY] 成功: {stats.success}")
    print(f"[SUMMARY] 失败: {stats.failed}")
    print(f"[SUMMARY] 无EXIF日期(归档到000000): {stats.unknown_date}")
    print(f"[SUMMARY] 总耗时: {elapsed_seconds:.2f}s")


def get_photo_date_code(file_path: Path) -> str:
    shot_at = get_exif_datetime_original(file_path)
    if shot_at is None:
        return "000000"
    return shot_at.strftime("%y%m%d")


def get_exif_datetime_original(file_path: Path) -> datetime | None:
    try:
        with Image.open(file_path) as image:
            exif = image.getexif()
            if not exif:
                return None

            # 36867 = DateTimeOriginal，部分图片也可能只存在 306 = DateTime。
            raw_value = exif.get(36867) or exif.get(306)
            if not raw_value:
                return None

            return datetime.strptime(str(raw_value), "%Y:%m:%d %H:%M:%S")
    except (FileNotFoundError, PermissionError, UnidentifiedImageError, ValueError, OSError):
        return None


def unique_target_path(dir_path: Path, name: str) -> Path:
    target_path = dir_path / name
    if not target_path.exists():
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix

    for index in range(1, 10000):
        candidate = dir_path / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"cannot find free target name for {name}")


def copy_file(src: Path, dst: Path) -> None:
    shutil.copy2(src, dst)


if __name__ == "__main__":
    main()