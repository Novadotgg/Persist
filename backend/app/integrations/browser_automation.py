import asyncio
import structlog
from typing import Dict, Any, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
browser_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)


class BrowserAutomationConnector:
    """
    Browser automation connector using Playwright (local headless Chromium).
    Supports page navigation, content extraction, form filling, and screenshots.
    
    Requires: playwright Python package + browser binaries installed.
    Install: pip install playwright && playwright install chromium
    
    Optional Browserbase cloud fallback: set BROWSERBASE_API_KEY and
    BROWSERBASE_PROJECT_ID in .env to run sessions in the cloud instead of locally.
    """

    @staticmethod
    @browser_circuit_breaker
    async def navigate_and_screenshot(
        url: str,
        output_path: str = "screenshot.png",
        wait_for_selector: Optional[str] = None,
        timeout_ms: int = 30000,
        browserbase_api_key: Optional[str] = None,
        browserbase_project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Navigates to a URL, waits for the page to load, and takes a screenshot.
        Returns screenshot file path and page title.
        
        If browserbase_api_key and project_id are provided, uses Browserbase cloud.
        Otherwise falls back to local headless Chromium.
        """
        logger.info("Browser: navigating to URL", url=url)

        # Try Browserbase cloud if credentials provided
        if browserbase_api_key and browserbase_project_id:
            return await BrowserAutomationConnector._browserbase_screenshot(
                url=url,
                output_path=output_path,
                api_key=browserbase_api_key,
                project_id=browserbase_project_id,
                wait_for_selector=wait_for_selector,
                timeout_ms=timeout_ms,
            )

        # Local Playwright
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                if wait_for_selector:
                    await page.wait_for_selector(wait_for_selector, timeout=timeout_ms)
                title = await page.title()
                await page.screenshot(path=output_path, full_page=False)
                logger.info("Browser screenshot taken", output=output_path, title=title)
                return {"title": title, "screenshot_path": output_path, "url": url}
            finally:
                await browser.close()

    @staticmethod
    @browser_circuit_breaker
    async def extract_page_text(
        url: str,
        selector: Optional[str] = None,
        timeout_ms: int = 30000,
    ) -> Dict[str, Any]:
        """
        Navigates to a URL and extracts visible text content.
        selector: optional CSS selector to restrict extraction to a specific element.
        Returns title and extracted text.
        """
        logger.info("Browser: extracting page text", url=url)
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                title = await page.title()
                if selector:
                    element = await page.query_selector(selector)
                    text = await element.inner_text() if element else ""
                else:
                    text = await page.inner_text("body")
                logger.info("Browser page text extracted", chars=len(text))
                return {"title": title, "text": text[:50000], "url": url}
            finally:
                await browser.close()

    @staticmethod
    @browser_circuit_breaker
    async def fill_form_and_submit(
        url: str,
        form_data: Dict[str, str],
        submit_selector: str = "button[type='submit']",
        timeout_ms: int = 30000,
    ) -> Dict[str, Any]:
        """
        Navigates to a URL, fills in a form with provided data, and clicks the submit button.
        form_data: dict mapping CSS selectors to values to fill, e.g. {"#email": "user@example.com"}
        Returns final URL after submission and page title.
        """
        logger.info("Browser: filling form", url=url, fields=list(form_data.keys()))
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                for selector, value in form_data.items():
                    await page.fill(selector, value)
                await page.click(submit_selector)
                await page.wait_for_load_state("networkidle", timeout=timeout_ms)
                final_url = page.url
                title = await page.title()
                logger.info("Browser form submitted", final_url=final_url)
                return {"final_url": final_url, "title": title, "status": "submitted"}
            finally:
                await browser.close()

    @staticmethod
    @browser_circuit_breaker
    async def click_element(
        url: str,
        selector: str,
        wait_after_ms: int = 2000,
        timeout_ms: int = 30000,
    ) -> Dict[str, Any]:
        """
        Navigates to a URL and clicks a specific element identified by a CSS selector.
        Returns the page URL and title after the click.
        """
        logger.info("Browser: clicking element", url=url, selector=selector)
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                await page.click(selector, timeout=timeout_ms)
                await asyncio.sleep(wait_after_ms / 1000)
                final_url = page.url
                title = await page.title()
                return {"final_url": final_url, "title": title, "clicked": selector}
            finally:
                await browser.close()

    @staticmethod
    async def _browserbase_screenshot(
        url: str,
        output_path: str,
        api_key: str,
        project_id: str,
        wait_for_selector: Optional[str],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        """
        Uses Browserbase cloud to create a browser session and take a screenshot.
        Requires the Playwright package for WebSocket CDP connection.
        """
        import httpx as _httpx

        logger.info("Browser: using Browserbase cloud session", url=url)
        # Create a Browserbase session
        async with _httpx.AsyncClient() as client:
            session_response = await client.post(
                "https://www.browserbase.com/v1/sessions",
                headers={
                    "X-BB-API-Key": api_key,
                    "Content-Type": "application/json",
                },
                json={"projectId": project_id},
            )
            if session_response.status_code not in [200, 201]:
                logger.error(
                    "Failed to create Browserbase session",
                    status_code=session_response.status_code,
                )
                session_response.raise_for_status()
            session_data = session_response.json()
            session_id = session_data.get("id")
            ws_url = session_data.get("connectUrl")

        if not ws_url:
            raise RuntimeError("Browserbase did not return a WebSocket connection URL.")

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(ws_url)
            context = browser.contexts[0]
            page = context.pages[0]
            await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=timeout_ms)
            title = await page.title()
            await page.screenshot(path=output_path)
            await browser.close()
            logger.info("Browserbase screenshot taken", session_id=session_id, title=title)
            return {
                "title": title,
                "screenshot_path": output_path,
                "url": url,
                "session_id": session_id,
            }
