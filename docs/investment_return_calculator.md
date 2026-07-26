# investment_return_calculator

理财投资收益计算器，用于按复利快速估算期末总金额、总投入和总收益，也支持根据本金、收益和持有月数反推年化收益率。

## 功能

- 按年化收益率和复利次数计算期末金额
- 支持周期追加投入
- 支持选择定投是在周期开始还是周期结束时投入
- 支持自定义货币符号
- 支持反算模式，根据本金、收益和持有月数计算年化收益率

## 用法

```bash
python scripts/investment_return_calculator.py --principal 100000 --annual-rate 5 --years 3
```

必填参数：

- `--principal`：初始本金，例如 `100000`
- `--annual-rate`：年化收益率百分比，例如 `5` 表示 5%
- `--years`：投资年限，例如 `3` 或 `3.5`

可选参数：

- `--compounds-per-year`：每年复利次数，默认 `12`
- `--periodic-contribution`：每个复利周期追加投入金额，默认 `0`
- `--beginning`：将定投视为每个周期开始时投入
- `--currency-symbol`：金额显示符号，默认 `元`

## 反算模式

当你已经知道投入本金、实际收益和持有月数时，可以使用反算模式直接计算年化收益率：

```bash
python scripts/investment_return_calculator.py --reverse --principal 40000 --interest 140 --months 2
```

反算模式参数说明：

- `--reverse`：启用反算模式
- `--principal`：初始本金，必须大于 `0`
- `--interest`：总收益金额
- `--months`：持有月数，例如 `2`、`3`

计算公式：

- 年化收益率 = `(1 + 收益 / 本金) ^ (12 / 持有月数) - 1`

## 示例

```bash
python scripts/investment_return_calculator.py --principal 100000 --annual-rate 4.8 --years 5 --periodic-contribution 2000 --beginning
```

## 输出说明

脚本会输出以下结果：

- 初始本金
- 年化收益率
- 投资年限
- 每年复利次数
- 周期追加投入
- 投入时点
- 期末总金额
- 总投入金额
- 总收益

反算模式会输出以下结果：

- 初始本金
- 总收益
- 持有月数
- 总回报率
- 年化收益率
- 期末总金额