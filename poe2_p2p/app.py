from __future__ import annotations

import argparse
from pathlib import Path

from .alerts import filter_profit_alerts
from .calculator import ArbitrageCalculator
from .calibration import load_region, save_region
from .config import DEFAULT_MARKET_RATIO_REGION, CropRegion
from .dashboard import export_history_dashboard
from .diagnostics import run_diagnostics
from .exporter import export_opportunities_csv
from .icon_cache import cache_poe_ninja_icons
from .logging_utils import configure_logging
from .parser import parse_ratio
from .poe_ninja import fetch_currency_candidates
from .presets import DEFAULT_PRESETS, get_preset
from .ranking import rank_opportunities
from .sample_data import EXALTED, screenshot_rates
from .storage import SQLiteStore
from .updater import check_for_updates
from .validation import validate_ratio_range


def build_sample_opportunities(
    max_hops: int = 3,
    input_amount: float = 2050.0,
    start_currency: str = EXALTED,
    slippage_buffer_percent: float = 0.0,
    spread_loss_percent: float = 0.0,
    rounding_loss_flat: float = 0.0,
    gold_cost_flat: float = 0.0,
    rounding_loss_per_step: float = 0.0,
    gold_cost_per_step: float = 0.0,
    stale_penalty_percent: float = 0.0,
    low_confidence_penalty_percent: float = 0.0,
    seconds_per_step: float = 0.0,
    min_bankroll: float = 0.0,
    cycles_per_hour: float = 1.0,
    min_roi_percent: float = 0.0,
):
    rates = screenshot_rates()
    calculator = ArbitrageCalculator(
        rates,
        slippage_buffer_percent=slippage_buffer_percent,
        spread_loss_percent=spread_loss_percent,
        rounding_loss_flat=rounding_loss_flat,
        gold_cost_flat=gold_cost_flat,
        rounding_loss_per_step=rounding_loss_per_step,
        gold_cost_per_step=gold_cost_per_step,
        stale_penalty_percent=stale_penalty_percent,
        low_confidence_penalty_percent=low_confidence_penalty_percent,
        seconds_per_step=seconds_per_step,
        min_bankroll=min_bankroll,
        cycles_per_hour=cycles_per_hour,
        min_roi_percent=min_roi_percent,
    )
    opportunities = calculator.find_cycles(
        start_currency=start_currency,
        input_amount=input_amount,
        max_hops=max_hops,
    )
    return rates, opportunities


def print_cli_table(opportunities=None) -> None:
    if opportunities is None:
        _, opportunities = build_sample_opportunities()
    headers = ("Path", "Input", "Output", "Net Profit", "ROI %", "Profit/h", "Risk", "Confidence")
    rows = [
        (
            opportunity.path_label,
            f"{opportunity.input_amount:.2f} {opportunity.input_currency}",
            f"{opportunity.output_amount:.2f} {opportunity.input_currency}",
            f"{opportunity.net_profit:.2f}",
            f"{opportunity.roi_percent:.2f}",
            f"{opportunity.profit_per_hour:.2f}",
            opportunity.risk,
            f"{opportunity.confidence:.2f}",
        )
        for opportunity in opportunities
        if opportunity.net_profit > 0
    ]
    if not rows:
        print("No profitable opportunities found.")
        return

    widths = [
        max(len(str(value)) for value in (header, *(row[index] for row in rows)))
        for index, header in enumerate(headers)
    ]
    print(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def persist_sample_run(database_path: Path) -> None:
    rates, opportunities = build_sample_opportunities()
    store = SQLiteStore(database_path)
    store.init_schema()
    store.save_rates(rates)
    store.save_opportunities(opportunities)


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true", help="Run without the PySide6 overlay")
    parser.add_argument("--ratio-text", help="Parse a market ratio string and exit")
    parser.add_argument("--ocr-image", help="Read a market ratio from an image file and exit")
    parser.add_argument("--capture-screen", help="Capture the configured screen region to this file")
    parser.add_argument(
        "--crop-image",
        help="Crop an image before OCR. Useful for testing screenshots.",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="Crop region as x,y,width,height. Defaults to the sample screenshot ratio region.",
    )
    parser.add_argument(
        "--crop-output",
        default="ratio_crop.png",
        help="Output path for --crop-image",
    )
    parser.add_argument("--save-calibration", help="Save --region to a calibration JSON file")
    parser.add_argument("--load-calibration", help="Load crop region from a calibration JSON file")
    parser.add_argument("--export-csv", help="Export sample opportunities to CSV")
    parser.add_argument("--alert-profit", type=float, default=None, help="Print alerts above net profit")
    parser.add_argument("--alert-roi", type=float, default=0.0, help="Alert ROI threshold")
    parser.add_argument("--history", type=int, default=None, help="Show recent stored opportunities")
    parser.add_argument("--history-dashboard", help="Export recent history dashboard HTML")
    parser.add_argument("--list-presets", action="store_true", help="List available calculation presets")
    parser.add_argument("--fetch-candidates", action="store_true", help="Fetch and print poe.ninja shortlist")
    parser.add_argument("--poe-ninja-url", default=None, help="Override poe.ninja currency URL")
    parser.add_argument("--poe-ninja-league", default=None, help="Override poe.ninja POE2 league")
    parser.add_argument("--candidate-limit", type=int, default=25)
    parser.add_argument("--cache-icons", action="store_true", help="Download poe.ninja icons into local cache")
    parser.add_argument("--icon-cache-dir", default="icon_cache")
    parser.add_argument("--check-update", action="store_true", help="Check GitHub Releases for updates")
    parser.add_argument("--diagnostics", action="store_true", help="Запустить диагностику и сохранить отчет")
    parser.add_argument("--diagnostics-live", action="store_true", help="Проверить живой снимок экрана и OCR")
    parser.add_argument("--diagnostics-output", default=None, help="Путь к отчету диагностики")
    parser.add_argument("--min-volume", type=float, default=0.0)
    parser.add_argument("--validate-rate", type=float, default=None, help="Observed rate to validate")
    parser.add_argument("--expected-rate", type=float, default=None, help="Expected rate for --validate-rate")
    parser.add_argument("--rate-tolerance", type=float, default=20.0)
    parser.add_argument("--preset", default="exalted-direct", help="Calculation preset name")
    parser.add_argument("--max-hops", type=int, default=None, help="Override preset max hops")
    parser.add_argument("--rank-by", default="net_profit", help="net_profit, roi, profit_per_hour, score, confidence")
    parser.add_argument("--cycles-per-hour", type=float, default=1.0)
    parser.add_argument("--slippage-percent", type=float, default=0.0)
    parser.add_argument("--spread-percent", type=float, default=0.0)
    parser.add_argument("--rounding-loss", type=float, default=0.0)
    parser.add_argument("--gold-cost", type=float, default=0.0)
    parser.add_argument("--rounding-loss-per-step", type=float, default=0.0)
    parser.add_argument("--gold-cost-per-step", type=float, default=0.0)
    parser.add_argument("--stale-penalty-percent", type=float, default=0.0)
    parser.add_argument("--low-confidence-penalty-percent", type=float, default=0.0)
    parser.add_argument("--seconds-per-step", type=float, default=0.0)
    parser.add_argument("--min-bankroll", type=float, default=0.0)
    parser.add_argument(
        "--db",
        default="poe2_p2p.db",
        help="SQLite database path",
    )
    args = parser.parse_args(argv)

    if args.ratio_text:
        left, right = parse_ratio(args.ratio_text)
        print(f"Parsed ratio: {left:g} : {right:g}")
        return 0

    if args.list_presets:
        for preset in DEFAULT_PRESETS.values():
            print(
                f"{preset.name}: base={preset.base_currency}, "
                f"input={preset.input_amount:g}, min_roi={preset.min_roi_percent:g}, "
                f"max_hops={preset.max_hops}, chain_type={preset.chain_type.value}"
            )
        return 0

    if args.fetch_candidates:
        candidates = fetch_currency_candidates(
            url=args.poe_ninja_url or None,
            league=args.poe_ninja_league,
            limit=args.candidate_limit,
            min_volume_per_hour=args.min_volume,
        )
        for candidate in candidates:
            print(
                f"{candidate.name} | chaos={candidate.value_in_chaos:g} | "
                f"volume/h={candidate.volume_per_hour:g} | "
                f"7d={candidate.seven_day_change_percent:g}% | "
                f"score={candidate.volume_score:g}"
            )
        return 0

    if args.cache_icons:
        count = cache_poe_ninja_icons(
            cache_dir=args.icon_cache_dir,
            league=args.poe_ninja_league,
            limit=args.candidate_limit,
        )
        print(f"Загружено новых иконок: {count}")
        return 0

    if args.check_update:
        status = check_for_updates()
        print(status.message)
        if status.download_url:
            print(status.download_url)
        return 0 if status.checked else 2

    if args.diagnostics:
        report = run_diagnostics(
            live_capture=args.diagnostics_live,
            report_path=args.diagnostics_output,
        )
        print(report.text)
        print(f"\nОтчет сохранен: {report.report_path}")
        return 0 if report.ok else 4

    if args.validate_rate is not None:
        if args.expected_rate is None:
            parser.error("--validate-rate requires --expected-rate")
        result = validate_ratio_range(
            observed_rate=args.validate_rate,
            expected_rate=args.expected_rate,
            tolerance_percent=args.rate_tolerance,
        )
        print(f"Rate validation: {'OK' if result.ok else 'FAILED'} - {result.reason}")
        return 0 if result.ok else 3

    if args.load_calibration:
        region = load_region(args.load_calibration)
    elif args.region:
        region = CropRegion.from_csv(args.region)
    else:
        region = DEFAULT_MARKET_RATIO_REGION

    if args.save_calibration:
        save_region(args.save_calibration, region)
        print(
            f"Saved calibration {region.x},{region.y},{region.width},{region.height} "
            f"to {args.save_calibration}"
        )
        return 0

    if args.crop_image:
        from .capture import crop_image_file

        crop_image_file(args.crop_image, region, args.crop_output)
        print(f"Cropped {args.crop_image} -> {args.crop_output}")
        return 0

    if args.capture_screen:
        from .capture import capture_screen_region

        capture_screen_region(region, args.capture_screen)
        print(f"Captured screen region -> {args.capture_screen}")
        return 0

    if args.ocr_image:
        from .ocr import OCRDependencyError, read_ratio_from_image

        try:
            result = read_ratio_from_image(args.ocr_image)
        except OCRDependencyError as error:
            print(f"OCR unavailable: {error}")
            return 2
        left, right = result.ratio
        print(f"OCR text: {result.raw_text}")
        print(f"Parsed ratio: {left:g} : {right:g}")
        print(f"Confidence: {result.confidence:.2f}")
        return 0

    preset = get_preset(args.preset)
    max_hops = args.max_hops if args.max_hops is not None else preset.max_hops
    rates, opportunities = build_sample_opportunities(
        start_currency=preset.base_currency,
        input_amount=preset.input_amount,
        max_hops=max_hops,
        slippage_buffer_percent=args.slippage_percent,
        spread_loss_percent=args.spread_percent,
        rounding_loss_flat=args.rounding_loss,
        gold_cost_flat=args.gold_cost,
        rounding_loss_per_step=args.rounding_loss_per_step,
        gold_cost_per_step=args.gold_cost_per_step,
        stale_penalty_percent=args.stale_penalty_percent,
        low_confidence_penalty_percent=args.low_confidence_penalty_percent,
        seconds_per_step=args.seconds_per_step,
        min_bankroll=args.min_bankroll,
        cycles_per_hour=args.cycles_per_hour,
        min_roi_percent=preset.min_roi_percent,
    )
    opportunities = rank_opportunities(opportunities, key=args.rank_by)

    store = SQLiteStore(Path(args.db))
    store.init_schema()
    store.save_rates(rates)
    store.save_opportunities(opportunities)

    if args.history is not None:
        for row in store.list_recent_opportunities(args.history):
            print(
                f"{row['created_at']} | {row['path']} | "
                f"net={row['net_profit']:.2f} | roi={row['roi_percent']:.2f}% | "
                f"score={row['score']:.2f} | risk={row['risk']}"
            )
        print(f"Total recorded net profit: {store.total_recorded_net_profit():.2f}")
        return 0

    if args.history_dashboard:
        rows = store.list_recent_opportunities(200)
        export_history_dashboard(rows, args.history_dashboard)
        print(f"Exported history dashboard -> {args.history_dashboard}")
        return 0

    if args.export_csv:
        export_opportunities_csv(opportunities, args.export_csv)
        print(f"Exported opportunities -> {args.export_csv}")
        return 0

    if args.alert_profit is not None:
        alerts = filter_profit_alerts(
            opportunities,
            min_net_profit=args.alert_profit,
            min_roi_percent=args.alert_roi,
        )
        print_cli_table(alerts)
        return 0

    if args.cli:
        print_cli_table(opportunities)
        return 0

    try:
        from .ui.overlay import run_overlay
    except ImportError as error:
        print(f"PySide6 overlay is unavailable: {error}")
        print("Run with --cli or install requirements.txt")
        print_cli_table()
        return 1

    return run_overlay(opportunities)


if __name__ == "__main__":
    raise SystemExit(main())
