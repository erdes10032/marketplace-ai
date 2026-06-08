from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from playwright._impl._errors import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.brands.normalize import JS_NORMALIZE_BRAND, normalize_brand_token
from app.parsers.models import ProductSummary
from app.parsers.types import ManualWaitCallback
from app.utils.log import log

_STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
"""

class WBBrowserCollector:
    def __init__(
        self,
        *,
        headless: bool = False,
        timeout_ms: int = 60000,
        wait_captcha: bool = True,
        profile_dir: Path,
        cdp_url: str | None = None,
        manual_wait: ManualWaitCallback | None = None,
    ) -> None:
        self.headless = headless
        self.wait_captcha = wait_captcha
        self.timeout_ms = timeout_ms
        self.cdp_url = cdp_url
        self.profile_dir = profile_dir
        self.manual_wait = manual_wait

    def collect(
        self,
        *,
        brand_input: str,
        max_products: int,
        max_scrolls: int,
    ) -> list[ProductSummary]:
        if self.headless and not self.cdp_url:
            log("WBParser", "Внимание: headless часто блокируется антиботом WB.")

        with sync_playwright() as playwright:
            if self.cdp_url:
                log("WBParser", f"Подключение к Chrome: {self.cdp_url}")
                browser = playwright.chromium.connect_over_cdp(self.cdp_url)
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.pages[0] if context.pages else context.new_page()
                try:
                    brand_url = self._open_brand_catalog_page(page, brand_input)
                    log("WBParser", f"Страница каталога: {brand_url}")
                    return self._extract_products_from_page(page, max_products, max_scrolls)
                finally:
                    browser.close()

            context, page = self._open_browser(playwright)
            try:
                brand_url = self._open_brand_catalog_page(page, brand_input)
                log("WBParser", f"Страница каталога: {brand_url}")
                return self._extract_products_from_page(page, max_products, max_scrolls)
            finally:
                context.close()

    def _open_browser(self, playwright):
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        log("WBParser", f"Профиль браузера: {self.profile_dir}")

        launch_kwargs = {
            "user_data_dir": str(self.profile_dir),
            "headless": self.headless,
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
            "viewport": {"width": 1440, "height": 900},
            "args": ["--disable-blink-features=AutomationControlled"],
            "ignore_default_args": ["--enable-automation"],
            "extra_http_headers": {
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        }

        context = None
        for channel in ("chrome", None):
            try:
                if channel:
                    context = playwright.chromium.launch_persistent_context(
                        channel=channel,
                        **launch_kwargs,
                    )
                else:
                    context = playwright.chromium.launch_persistent_context(**launch_kwargs)
                break
            except PlaywrightError:
                continue

        if context is None:
            raise RuntimeError(
                "Не удалось запустить браузер. Установите Google Chrome или выполните: "
                "python -m playwright install chromium"
            )

        context.add_init_script(_STEALTH_INIT_SCRIPT)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(self.timeout_ms)
        return context, page

    @staticmethod
    def _is_antibot_page(page: Page) -> bool:
        try:
            body = page.locator("body").inner_text(timeout=3000).lower()
        except PlaywrightTimeoutError:
            return True
        markers = (
            "подозрительная активность",
            "почти готово",
            "пожалуйста, подождите",
            "captcha-support",
            "__wbaas/challenges",
        )
        if any(marker in body for marker in markers):
            return True
        return "__wbaas/challenges" in page.url

    def _wait_through_antibot(self, page: Page, label: str) -> None:
        if not self._is_antibot_page(page):
            return

        log(
            "WBParser",
            "Anti-bot на «"
            f"{label}"
            "»: таймер обновляет страницу снова и снова, потому что WB считает "
            "браузер ботом. По умолчанию товары берутся через API (без браузера). "
            "Для браузера используйте --cdp-url к обычному Chrome.",
        )

        if self.cdp_url and self.wait_captcha and not self.headless:
            if self.manual_wait is not None:
                self.manual_wait(
                    "[WBParser] В подключённом Chrome откройте/обновите wildberries.ru, "
                    "дождитесь нормальной страницы, затем нажмите Enter здесь."
                )
            page.wait_for_timeout(1000)
            if not self._is_antibot_page(page):
                return

        raise RuntimeError(
            "Wildberries anti-bot: автоматический браузер не проходит проверку. "
            "Запустите без --use-browser (API) или с --cdp-url http://127.0.0.1:9222 "
            "после открытия WB в обычном Chrome."
        )

    def _warmup_session(self, page: Page) -> None:
        log("WBParser", "Прогрев сессии на wildberries.ru...")
        page.goto("https://www.wildberries.ru/", wait_until="domcontentloaded")
        self._wait_through_antibot(page, "главная")
        self._wait_for_content(page, link_selector="a", steps=30, label="главная")
        page.wait_for_timeout(1500)

    def _open_brand_catalog_page(self, page: Page, brand_input: str) -> str:
        self._warmup_session(page)
        candidate = brand_input.strip()

        if candidate.startswith("http://") or candidate.startswith("https://"):
            parsed = urlparse(candidate)
            if "wildberries.ru" not in parsed.netloc:
                raise ValueError("Ожидается ссылка на wildberries.ru")
            return self._open_brand_via_brandlist_by_slug(page, candidate)

        return self._open_brand_via_brandlist_by_name(page, candidate)

    def _open_brand_via_brandlist_by_name(self, page: Page, brand_name: str) -> str:
        log("WBParser", "Открываю brandlist/all и ищу бренд...")
        page.goto("https://www.wildberries.ru/brandlist/all", wait_until="domcontentloaded")
        self._wait_through_antibot(page, "brandlist")
        self._wait_for_content(page, link_selector="a[href*='/brands/']", steps=30, label="brandlist")
        page.wait_for_timeout(1000)

        target_norm = normalize_brand_token(brand_name)
        self._filter_brandlist(page, brand_name)

        clicked = self._click_brand_link(page, target_norm)
        if not clicked:
            raise RuntimeError(
                f"Не удалось найти бренд '{brand_name}' на странице brandlist/all."
            )

        self._wait_for_brand_catalog(page)
        if self._is_error_page(page):
            raise RuntimeError(
                f"Страница бренда '{brand_name}' недоступна в автоматическом браузере. "
                "Попробуйте запуск без --headless."
            )
        return page.url

    def _open_brand_via_brandlist_by_slug(self, page: Page, brand_url: str) -> str:
        slug = brand_url.rstrip("/").split("/")[-1]
        brand_key = normalize_brand_token(slug.replace("-", " "))

        log("WBParser", "Открываю brandlist/all для перехода по ссылке бренда...")
        page.goto("https://www.wildberries.ru/brandlist/all", wait_until="domcontentloaded")
        self._wait_through_antibot(page, "brandlist")
        self._wait_for_content(page, link_selector="a[href*='/brands/']", steps=30, label="brandlist")
        page.wait_for_timeout(1000)

        slug_tail = slug.lower()
        link_locator = page.locator(f"a[href*='/brands/{slug_tail}']")
        if link_locator.count() == 0:
            link_locator = page.locator(f"a[href*='{slug_tail}']")

        if link_locator.count() > 0:
            log("WBParser", "Перехожу на страницу бренда кликом из brandlist...")
            with page.expect_navigation(wait_until="domcontentloaded", timeout=self.timeout_ms):
                link_locator.first.click()
        else:
            clicked = self._click_brand_link(page, brand_key)
            if not clicked:
                raise RuntimeError(f"Не удалось открыть бренд по URL: {brand_url}")

        self._wait_for_brand_catalog(page)
        if self._is_error_page(page):
            raise RuntimeError(
                "Страница бренда открылась с ошибкой. Запустите без --headless "
                "или проверьте доступ к Wildberries."
            )
        return page.url

    @staticmethod
    def _filter_brandlist(page: Page, brand_name: str) -> None:
        if page.locator("input").count() == 0:
            return
        page.evaluate(
            """(value) => {
            const inputs = Array.from(document.querySelectorAll("input"));
            const input = inputs.find((el) => {
                const ph = (el.getAttribute("placeholder") || "").toLowerCase();
                const nm = (el.getAttribute("name") || "").toLowerCase();
                return ph.includes("бренд")
                    || ph.includes("поиск")
                    || nm.includes("search")
                    || nm.includes("query");
            }) || inputs[0];
            if (!input) return;
            input.focus();
            input.value = value;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
            brand_name,
        )
        page.wait_for_timeout(1200)

    def _click_brand_link(self, page: Page, target_norm: str) -> bool:
        link_index = page.evaluate(
            JS_NORMALIZE_BRAND
            + """(targetNorm) => {
            const normalize = normalizeBrand;
            const links = Array.from(document.querySelectorAll("a[href*='/brands/']"));

            const pick = (predicate) => links.findIndex(predicate);
            let idx = pick((link) => normalize(link.textContent) === targetNorm);
            if (idx >= 0) return idx;

            idx = pick((link) => {
                const textNorm = normalize(link.textContent);
                return textNorm && (textNorm.includes(targetNorm) || targetNorm.includes(textNorm));
            });
            if (idx >= 0) return idx;

            idx = pick((link) => {
                const hrefNorm = normalize(link.getAttribute("href"));
                return hrefNorm.includes(targetNorm);
            });
            return idx;
        }""",
            target_norm,
        )
        if link_index is None or link_index < 0:
            return False

        brand_link = page.locator("a[href*='/brands/']").nth(int(link_index))
        log("WBParser", "Перехожу на страницу бренда кликом (в той же сессии)...")
        with page.expect_navigation(wait_until="domcontentloaded", timeout=self.timeout_ms):
            brand_link.click()
        self._wait_through_antibot(page, "страница бренда")
        return True

    def _wait_for_content(
        self, page: Page, link_selector: str, steps: int, label: str
    ) -> None:
        for attempt in range(1, steps + 1):
            if self._is_antibot_page(page):
                self._wait_through_antibot(page, label)
            if page.locator(link_selector).count() > 0:
                return
            page.wait_for_timeout(1000)
            if attempt % 10 == 0:
                log(
                    "WBParser",
                    f"Ожидаю контент ({label})... попытка {attempt}/{steps}",
                )

    def _wait_for_brand_catalog(self, page: Page) -> None:
        self._wait_through_antibot(page, "каталог бренда")
        self._wait_for_content(
            page,
            link_selector="a[href*='/catalog/'][href*='/detail.aspx']",
            steps=40,
            label="каталог бренда",
        )
        page.wait_for_timeout(1500)

    @staticmethod
    def _is_error_page(page: Page) -> bool:
        body = page.locator("body").inner_text().lower()
        markers = (
            "страница не найдена",
            "страницы не существует",
            "такой страницы нет",
            "page not found",
            "404",
        )
        return any(marker in body for marker in markers)

    def _extract_products_from_page(
        self,
        page: Page,
        max_products: int,
        max_scrolls: int,
    ) -> list[ProductSummary]:
        if self._is_error_page(page):
            raise RuntimeError(
                "На странице бренда отображается ошибка (страница не найдена). "
                "Используйте запуск без --headless."
            )

        for _ in range(max_scrolls):
            count = page.locator("a[href*='/catalog/'][href*='/detail.aspx']").count()
            if count >= max_products:
                break
            page.mouse.wheel(0, 10000)
            page.wait_for_timeout(350)

        raw_links_count = page.locator("a[href*='/catalog/'][href*='/detail.aspx']").count()
        log("WBParser", f"Найдено ссылок на карточки: {raw_links_count}")

        cards = page.evaluate(
            """() => {
            const cardSelectors = [
                "article.product-card",
                "div.product-card",
                "li.product-card",
                "[data-nm-id]",
            ];
            const cardNodes = [];
            for (const selector of cardSelectors) {
                for (const node of document.querySelectorAll(selector)) {
                    cardNodes.push(node);
                }
            }

            const linksFromCards = [];
            for (const node of cardNodes) {
                const linkEl = node.querySelector("a[href*='/catalog/'][href*='/detail.aspx']");
                if (linkEl && linkEl.href) linksFromCards.push({ node, href: linkEl.href });
            }

            const allLinks = Array.from(document.querySelectorAll("a[href*='/catalog/'][href*='/detail.aspx']"))
                .filter((el) => el.href)
                .map((el) => ({ node: el.closest("article, div, li") || el.parentElement || el, href: el.href }));

            const nodes = linksFromCards.length ? linksFromCards : allLinks;
            const result = [];
            for (const node of nodes) {
                const href = node.href;
                const match = href.match(/\\/catalog\\/(\\d+)\\/detail\\.aspx/);
                if (!match) continue;
                const nmId = Number(match[1]);
                const root = node.node || document;
                const title = root.querySelector(".product-card__name, .product-card__brand-wrap, .brand-name, [class*='name']")
                    ?.textContent?.trim() || `nm_${nmId}`;
                const ratingRaw = root.querySelector(".address-rate-mini")?.textContent?.trim()
                    || root.querySelector(".product-card__rating-wrap")?.textContent?.trim()
                    || root.querySelector("[class*='rating']")?.textContent?.trim()
                    || "";
                const rating = Number(ratingRaw.replace(",", "."));
                result.push({
                    nm_id: nmId,
                    title,
                    product_url: href,
                    rating: Number.isNaN(rating) ? null : rating,
                    brand_name: title.includes("/") ? title.split("/")[0].trim() : ""
                });
            }
            return result;
        }"""
        )

        seen: set[int] = set()
        products: list[ProductSummary] = []
        for raw in cards:
            nm_id = int(raw["nm_id"])
            if nm_id in seen:
                continue
            seen.add(nm_id)
            products.append(
                ProductSummary(
                    nm_id=nm_id,
                    title=raw.get("title") or f"nm_{nm_id}",
                    product_url=raw.get("product_url")
                    or f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx",
                    rating=raw.get("rating"),
                    brand_name=raw.get("brand_name"),
                )
            )
            if len(products) >= max_products:
                break
        return products
