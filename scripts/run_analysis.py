from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from app.database import create_session
from app.parsers.wb_parser import WBParser
from app.pipeline.analysis import BrandAnalysisPipeline
from app.reporting.writer import ReportWriter
from app.repositories.analysis_store import AnalysisStore
from app.utils.stdio import configure_utf8_stdio


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Анализ скрытых причин недовольства по бренду Wildberries"
    )
    parser.add_argument(
        "--brand",
        required=True,
        help="Slug бренда или ссылка, например scan-to или https://www.wildberries.ru/brands/scan-to",
    )
    parser.add_argument("--max-products", type=int, default=120)
    parser.add_argument("--max-reviews-per-product", type=int, default=120)
    parser.add_argument("--top", type=int, default=10, help="Сколько проблем показать")
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Папка для файлов отчета (csv/json)",
    )
    parser.add_argument(
        "--save-db",
        action="store_true",
        help="Сохранить продукты, отзывы и проблемные кластеры в БД",
    )
    parser.add_argument(
        "--include-neutral",
        action="store_true",
        help="Учитывать и отзывы с 4-5 звездами",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Запускать браузер Playwright в headless режиме (может блокироваться антиботом)",
    )
    parser.add_argument(
        "--no-wait-captcha",
        action="store_true",
        help="Не ждать ручного прохождения anti-bot (только автоматическое ожидание)",
    )
    parser.add_argument(
        "--cdp-url",
        default=None,
        help="Подключиться к уже открытому Chrome (например http://127.0.0.1:9222), "
        "если API не нашёл товары",
    )
    parser.add_argument(
        "--use-browser",
        action="store_true",
        help="Пробовать Playwright-браузер, если API не нашёл товары (часто блокируется)",
    )
    return parser.parse_args()


def main() -> None:
    configure_utf8_stdio()
    args = _parse_args()

    wb_parser = WBParser(
        headless=args.headless,
        wait_captcha=not args.no_wait_captcha,
        cdp_url=args.cdp_url,
        use_browser=args.use_browser,
    )
    result = BrandAnalysisPipeline(parser=wb_parser).run(
        args.brand,
        max_products=args.max_products,
        max_reviews_per_product=args.max_reviews_per_product,
        include_neutral=args.include_neutral,
        top=args.top,
    )
    if result is None:
        return

    ReportWriter.print_summary(result)
    csv_path, json_path = ReportWriter().write(result, Path(args.output_dir))
    print()
    print(f"CSV отчет сохранен: {csv_path}")
    print(f"JSON отчет сохранен: {json_path}")

    if args.save_db:
        session = create_session()
        try:
            AnalysisStore(session).save(result)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        print("Результаты анализа сохранены в БД.")


if __name__ == "__main__":
    main()
