from __future__ import annotations

import time
from pathlib import Path

from app.brands.resolver import BrandResolver
from app.parsers.models import ProductSummary, ReviewItem
from app.parsers.wb.browser import WBBrowserCollector
from app.parsers.wb.catalog import ensure_imt_ids
from app.parsers.wb.http import create_wb_session
from app.parsers.wb.product_collector import WBProductCollector
from app.parsers.types import ManualWaitCallback
from app.parsers.wb.review_fetcher import WBReviewFetcher
from app.utils.log import log


class WBParser:
    def __init__(
        self,
        headless: bool = False,
        timeout_ms: int = 60000,
        wait_captcha: bool = True,
        profile_dir: str | Path | None = None,
        cdp_url: str | None = None,
        use_browser: bool = False,
        manual_wait: ManualWaitCallback | None = None,
    ):
        self.cdp_url = cdp_url
        self.use_browser = use_browser
        self.profile_dir = Path(profile_dir or Path(__file__).resolve().parents[2] / ".wb_browser_profile")

        self._session = create_wb_session()
        self._brands = BrandResolver(self._session)
        self._product_collector = WBProductCollector(self._session, self._brands)
        self._review_fetcher = WBReviewFetcher(self._session)
        self._browser_collector = WBBrowserCollector(
            headless=headless,
            timeout_ms=timeout_ms,
            wait_captcha=wait_captcha,
            profile_dir=self.profile_dir,
            cdp_url=cdp_url,
            manual_wait=manual_wait or _default_manual_wait,
        )

    def parse_brand_reviews(
        self,
        brand_input: str,
        max_products: int = 200,
        max_reviews_per_product: int = 200,
        max_scrolls: int = 100,
    ) -> list[ReviewItem]:
        log("WBParser", "Сбор карточек товаров...")
        products = self._collect_products(
            brand_input=brand_input,
            max_products=max_products,
            max_scrolls=max_scrolls,
        )
        products = self._product_collector.filter_by_brand(products, brand_input)
        log("WBParser", f"Найдено товаров: {len(products)}")

        missing_count = sum(1 for product in products if product.imt_id is None)
        if missing_count:
            log(
                "WBParser",
                f"Определяю imt_id для {missing_count} товаров (нужно для отзывов)...",
            )
        ensure_imt_ids(self._session, products)

        reviews: list[ReviewItem] = []
        reviews_by_imt: dict[int, list[ReviewItem]] = {}
        for idx, product in enumerate(products, start=1):
            log(
                "WBParser",
                f"[{idx}/{len(products)}] Товар "
                f"nm_id={product.nm_id} imt_id={product.imt_id} | {product.title}",
            )
            imt_id = product.imt_id
            if not imt_id:
                log("WBParser", f"[{idx}/{len(products)}] Пропуск: нет imt_id")
                continue

            if imt_id in reviews_by_imt:
                log(
                    "WBParser",
                    f"[{idx}/{len(products)}] Отзывы уже загружены "
                    f"для imt_id={imt_id} (варианты одной карточки WB)",
                )
                continue

            product_reviews = self._review_fetcher.fetch_product_reviews(
                nm_id=product.nm_id,
                imt_id=imt_id,
                product_title=product.title,
                product_rating=product.rating,
                max_reviews=max_reviews_per_product,
            )
            reviews_by_imt[imt_id] = product_reviews
            reviews.extend(product_reviews)
            log(
                "WBParser",
                f"[{idx}/{len(products)}] Получено уникальных отзывов: "
                f"{len(product_reviews)} (всего уникальных: {len(reviews)})",
            )
            time.sleep(0.2)

        log("WBParser", f"Сбор отзывов завершен. Итого: {len(reviews)}")
        return reviews

    def _collect_products(
        self,
        brand_input: str,
        max_products: int,
        max_scrolls: int,
    ) -> list[ProductSummary]:
        brand_name = self._brands.resolve_name(brand_input)
        log("WBParser", f"Бренд для поиска: {brand_name}")

        products = self._product_collector.collect(
            brand_input=brand_input,
            brand_name=brand_name,
            max_products=max_products,
        )
        if products:
            return products

        log("WBParser", "Через API товары не найдены.")
        if self.cdp_url or self.use_browser:
            return self._browser_collector.collect(
                brand_input=brand_input,
                max_products=max_products,
                max_scrolls=max_scrolls,
            )

        raise RuntimeError(
            "Товары бренда не получены через API, а автоматический браузер WB блокирует "
            "(страница «Подозрительная активность» обновляется по кругу).\n\n"
            "Рекомендуемый способ — подключить ваш обычный Chrome:\n"
            '  1) Закройте все окна Chrome.\n'
            '  2) Запустите: chrome.exe --remote-debugging-port=9222 '
            '--user-data-dir="%LOCALAPPDATA%\\wb-chrome-profile"\n'
            "  3) В этом Chrome откройте https://www.wildberries.ru и дождитесь загрузки.\n"
            '  4) Запустите скрипт с флагом: --cdp-url http://127.0.0.1:9222\n\n'
            "Либо попробуйте: --use-browser (часто снова упирается в anti-bot)."
        )


def _default_manual_wait(message: str) -> None:
    input(f"{message}\n[WBParser] Enter после загрузки WB без anti-bot... ")
