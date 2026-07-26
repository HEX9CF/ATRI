# image_date_classifier

按图片的 EXIF 拍摄日期复制文件到日期目录。适合批量整理相册、导出的照片或混合目录中的图片文件。

## 功能

- 优先读取 `DateTimeOriginal`，其次回退到 `DateTimeDigitized`、`DateTime`，最后尝试 GPS 时间。
- 若 EXIF 无法读取，则使用文件创建时间或修改时间作为兜底。
- 输出目录会按日期自动分组；无法判断日期的文件会放到 `unknown`。
- 同名文件会自动追加序号，避免覆盖。

## 用法

```bash
python scripts/image_date_classifier.py [input_dir] [output_dir]
```

参数说明：

- `input_dir`：输入目录，默认 `input`
- `output_dir`：输出目录，默认 `output`

## 示例

```bash
python scripts/image_date_classifier.py photos sorted_photos
```

## 输出说明

- 日期正常识别时，文件会被复制到 `output/yyMMdd/`
- EXIF 取不到但能从文件时间兜底时，会复制到 `output/downgrade/yyMMdd/`
- 仍无法判断日期时，会复制到 `output/unknown/`

## 日志

- 运行时会在项目根目录的 `logs/` 目录下生成日志文件
- 终端与日志文件会输出处理进度、失败项和汇总结果