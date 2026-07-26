from __future__ import annotations

import argparse
import logging
import shutil
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from PIL import Image, UnidentifiedImageError


# 提升 Pillow 解压炸弹检测阈值，允许处理最高 5 亿像素图片。
Image.MAX_IMAGE_PIXELS = 500_000_000


@dataclass
class ProcessStats:
    total: int = 0
    processed: int = 0
    success: int = 0
    failed: int = 0
    unknown_date: int = 0
    warnings: int = 0


def main() -> None:
    args = parse_args()
    setup_logging()
    classify_files(args.input_dir, args.output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按图片 EXIF 拍摄日期复制文件到日期目录")
    parser.add_argument("input_dir", nargs="?", default="input", help="输入目录，默认 input")
    parser.add_argument("output_dir", nargs="?", default="output", help="输出目录，默认 output")
    return parser.parse_args()


def setup_logging() -> None:
    project_root = Path(__file__).resolve().parents[1]
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{datetime.now():%Y%m%d_%H%M%S}.log"
    logger = logging.getLogger("image_date_classifier")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info(f"[LOG] 输出文件: {log_file}")


def classify_files(input_dir: str, output_dir: str) -> None:
    logger = logging.getLogger("image_date_classifier")
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.is_dir():
        raise NotADirectoryError(f"input path is not a directory: {input_path}")

    output_path.mkdir(parents=True, exist_ok=True)

    files = [file_path for file_path in input_path.rglob("*") if file_path.is_file()]
    stats = ProcessStats(total=len(files))

    start_at = perf_counter()
    logger.info(f"[START] input={input_path} output={output_path}")
    logger.info(f"[INFO] 待处理文件总数: {stats.total}")

    if not files:
        print_summary(stats, perf_counter() - start_at)
        return

    for index, file_path in enumerate(files, start=1):
        try:
            date_code, warning_count, route_kind = get_photo_date_code(file_path)
            stats.warnings += warning_count
            if route_kind == "unknown":
                stats.unknown_date += 1

            if route_kind == "downgrade":
                target_dir = output_path / "downgrade" / date_code
            elif route_kind == "unknown":
                target_dir = output_path / "unknown"
            else:
                target_dir = output_path / date_code

            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = unique_target_path(target_dir, file_path.name)
            copy_file(file_path, target_path)

            stats.success += 1
            logger.info(
                f"[{index}/{stats.total}] OK  {file_path} -> {target_path} "
                f"({index / stats.total:.1%})"
            )
        except Exception as exc:
            stats.failed += 1
            logger.error(
                f"[{index}/{stats.total}] FAIL {file_path} "
                f"error={type(exc).__name__}: {exc} ({index / stats.total:.1%})"
            )
        finally:
            stats.processed += 1

    elapsed = perf_counter() - start_at
    print_summary(stats, elapsed)


def print_summary(stats: ProcessStats, elapsed_seconds: float) -> None:
    logger = logging.getLogger("image_date_classifier")
    logger.info("\n[SUMMARY] 处理完成")
    logger.info(f"[SUMMARY] 总数: {stats.total}")
    logger.info(f"[SUMMARY] 已处理: {stats.processed}")
    logger.info(f"[SUMMARY] 成功: {stats.success}")
    logger.info(f"[SUMMARY] 失败: {stats.failed}")
    logger.info(f"[SUMMARY] 警告: {stats.warnings}")
    logger.info(f"[SUMMARY] 无法处理(归档到unknown): {stats.unknown_date}")
    logger.info(f"[SUMMARY] 总耗时: {elapsed_seconds:.2f}s")


def get_photo_date_code(file_path: Path) -> tuple[str, int, str]:
    shot_at, warning_count = get_exif_datetime_original(file_path)
    if shot_at is None:
        fallback_at, fallback_warning_count = get_file_fallback_datetime(file_path)
        warning_count += fallback_warning_count
        if fallback_at is None:
            return "unknown", warning_count, "unknown"
        return fallback_at.strftime("%y%m%d"), warning_count, "downgrade"
    return shot_at.strftime("%y%m%d"), warning_count, "normal"


def get_file_fallback_datetime(file_path: Path) -> tuple[datetime | None, int]:
    try:
        stat_result = file_path.stat()
    except (FileNotFoundError, PermissionError, OSError):
        return None, 0

    timestamps: list[float] = []
    try:
        timestamps.append(stat_result.st_ctime)
    except AttributeError:
        pass

    try:
        timestamps.append(stat_result.st_mtime)
    except AttributeError:
        pass

    valid_times = [timestamp for timestamp in timestamps if timestamp > 0]
    if not valid_times:
        return None, 0

    return datetime.fromtimestamp(min(valid_times)), 0


def get_exif_datetime_original(file_path: Path) -> tuple[datetime | None, int]:
    try:
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            with Image.open(file_path) as image:
                exif = image.getexif()
                if not exif:
                    return None, len(caught_warnings)

                # 按精确性/可靠性从高到低兜底：Original -> Digitized -> Modify。
                candidates = [
                    (36867, 37521, 36881),  # DateTimeOriginal + SubSecTimeOriginal + OffsetTimeOriginal
                    (36868, 37522, 36882),  # DateTimeDigitized + SubSecTimeDigitized + OffsetTimeDigitized
                    (306, 37520, 36880),    # DateTime + SubSecTime + OffsetTime
                ]

                for base_tag, subsec_tag, offset_tag in candidates:
                    parsed = parse_exif_datetime(
                        exif.get(base_tag),
                        exif.get(subsec_tag),
                        exif.get(offset_tag),
                    )
                    if parsed is not None:
                        return parsed, len(caught_warnings)

                # 最后再用 GPS 时间兜底（通常是 UTC，且不一定等于快门时间）。
                parsed_gps = parse_gps_datetime(exif)
                if parsed_gps is not None:
                    return parsed_gps, len(caught_warnings)

                return None, len(caught_warnings)
    except (FileNotFoundError, PermissionError, UnidentifiedImageError, ValueError, OSError):
        return None, 0


def parse_exif_datetime(
    raw_value: Any,
    raw_subsec: Any = None,
    raw_offset: Any = None,
) -> datetime | None:
    if not raw_value:
        return None

    dt_str = str(raw_value).strip()
    if not dt_str:
        return None

    try:
        shot_at = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None

    if raw_subsec:
        subsec_digits = "".join(ch for ch in str(raw_subsec) if ch.isdigit())
        if subsec_digits:
            microsecond = int((subsec_digits + "000000")[:6])
            shot_at = shot_at.replace(microsecond=microsecond)

    # 目前仅用于按日期归档，时区可不做换算；若偏移格式异常则忽略。
    if raw_offset:
        offset_str = str(raw_offset).strip()
        if offset_str and len(offset_str) in (6, 3) and offset_str[0] in "+-":
            if len(offset_str) == 3:
                offset_str = f"{offset_str}:00"
            try:
                return datetime.fromisoformat(shot_at.strftime("%Y-%m-%dT%H:%M:%S.%f") + offset_str)
            except ValueError:
                pass

    return shot_at


def parse_gps_datetime(exif: Any) -> datetime | None:
    gps_info = None

    # Pillow 新老版本在 GPS IFD 读取方式上有差异。
    try:
        gps_info = exif.get_ifd(34853)
    except Exception:
        gps_info = exif.get(34853)

    if not gps_info:
        return None

    raw_date = gps_info.get(29)  # GPSDateStamp
    raw_time = gps_info.get(7)   # GPSTimeStamp
    if not raw_date or not raw_time:
        return None

    try:
        date_str = str(raw_date).strip().replace(":", "-")
        hours = int(float(raw_time[0]))
        minutes = int(float(raw_time[1]))
        seconds = int(float(raw_time[2]))
        return datetime.strptime(f"{date_str} {hours:02d}:{minutes:02d}:{seconds:02d}", "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, IndexError):
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