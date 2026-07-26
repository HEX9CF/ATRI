from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Final


DEFAULT_COMPOUNDS_PER_YEAR: Final[int] = 12
DEFAULT_CURRENCY_SYMBOL: Final[str] = "元"


@dataclass(frozen=True)
class CalculationResult:
    principal: float
    annual_rate: float
    years: float
    compounds_per_year: int
    periodic_contribution: float
    contribution_at_beginning: bool
    final_value: float
    total_contributed: float
    total_interest: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="理财投资收益计算器：按复利估算终值、总投入和收益"
    )
    parser.add_argument(
        "--principal",
        type=float,
        required=True,
        help="初始本金，例如 100000",
    )
    parser.add_argument(
        "--annual-rate",
        type=float,
        required=True,
        help="年化收益率百分比，例如 5 表示 5%%",
    )
    parser.add_argument(
        "--years",
        type=float,
        required=True,
        help="投资年限，例如 3 或 3.5",
    )
    parser.add_argument(
        "--compounds-per-year",
        type=int,
        default=DEFAULT_COMPOUNDS_PER_YEAR,
        help="每年复利次数，默认 12",
    )
    parser.add_argument(
        "--periodic-contribution",
        type=float,
        default=0.0,
        help="每个复利周期追加投入金额，默认 0",
    )
    parser.add_argument(
        "--beginning",
        action="store_true",
        help="将定投视为每个周期开始时投入，而不是周期结束时投入",
    )
    parser.add_argument(
        "--currency-symbol",
        default=DEFAULT_CURRENCY_SYMBOL,
        help="显示金额时使用的货币符号，默认 元",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.principal < 0:
        raise ValueError("principal must be >= 0")
    if args.years <= 0:
        raise ValueError("years must be > 0")
    if args.compounds_per_year <= 0:
        raise ValueError("compounds_per_year must be > 0")
    if args.periodic_contribution < 0:
        raise ValueError("periodic_contribution must be >= 0")


def calculate_result(args: argparse.Namespace) -> CalculationResult:
    periods = args.years * args.compounds_per_year
    periodic_rate = args.annual_rate / 100.0 / args.compounds_per_year

    if periodic_rate == 0:
        growth_factor = 1.0
        contribution_factor = periods
    else:
        growth_factor = (1.0 + periodic_rate) ** periods
        contribution_factor = ((1.0 + periodic_rate) ** periods - 1.0) / periodic_rate
        if args.beginning:
            contribution_factor *= 1.0 + periodic_rate

    final_value = args.principal * growth_factor + args.periodic_contribution * contribution_factor
    total_contributed = args.principal + args.periodic_contribution * periods
    total_interest = final_value - total_contributed

    return CalculationResult(
        principal=args.principal,
        annual_rate=args.annual_rate,
        years=args.years,
        compounds_per_year=args.compounds_per_year,
        periodic_contribution=args.periodic_contribution,
        contribution_at_beginning=args.beginning,
        final_value=final_value,
        total_contributed=total_contributed,
        total_interest=total_interest,
    )


def format_money(value: float, currency_symbol: str) -> str:
    return f"{currency_symbol}{value:,.2f}"


def print_result(result: CalculationResult, currency_symbol: str) -> None:
    timing_label = "期初投入" if result.contribution_at_beginning else "期末投入"
    print("理财投资收益计算结果")
    print(f"初始本金: {format_money(result.principal, currency_symbol)}")
    print(f"年化收益率: {result.annual_rate:.2f}%")
    print(f"投资年限: {result.years:.2f} 年")
    print(f"每年复利次数: {result.compounds_per_year}")
    print(f"周期追加投入: {format_money(result.periodic_contribution, currency_symbol)} / 周期")
    print(f"投入时点: {timing_label}")
    print(f"期末总金额: {format_money(result.final_value, currency_symbol)}")
    print(f"总投入金额: {format_money(result.total_contributed, currency_symbol)}")
    print(f"总收益: {format_money(result.total_interest, currency_symbol)}")


def main() -> None:
    args = parse_args()
    validate_args(args)
    result = calculate_result(args)
    print_result(result, args.currency_symbol)


if __name__ == "__main__":
    main()
