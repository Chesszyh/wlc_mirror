import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import cloudscraper
from rich.console import Console


class CookieManager:
    """Cookie管理器"""

    def __init__(self, cookie_file: str = "cookies.json"):
        self.cookie_file = Path(cookie_file)
        self.console = Console()

    def save_cookies(self, cookies: Dict[str, str], source: str = "manual"):
        """保存cookies到文件"""
        data = {
            "cookies": cookies,
            "timestamp": datetime.now().isoformat(),
            "source": source,
            # 设置7天过期
            "expires": (datetime.now() + timedelta(days=7)).isoformat(),
        }

        with open(self.cookie_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.console.print(f"[green]✅ Cookies已保存到 {self.cookie_file}[/green]")

    def load_cookies(self) -> Optional[Dict[str, str]]:
        """从文件加载cookies"""
        if not self.cookie_file.exists():
            return None

        try:
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查是否过期
            expires = datetime.fromisoformat(data.get("expires", "2000-01-01"))
            if datetime.now() > expires:
                self.console.print("[yellow]⚠️  Cookies已过期[/yellow]")
                return None

            cookies = data.get("cookies", {})
            self.console.print(
                f"[green]✅ 从文件加载Cookies ({data.get('source', 'unknown')})[/green]"
            )
            return cookies

        except Exception as e:
            self.console.print(f"[red]❌ 加载Cookies失败: {e}[/red]")
            return None

    def parse_cookie_string(self, cookie_string: str) -> Dict[str, str]:
        """解析Cookie字符串"""
        cookies = {}
        for item in cookie_string.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                cookies[key] = value
        return cookies


class TongjiAuthenticator:
    """同济课程网站认证器"""

    def __init__(self):
        self.base_url = "https://1.tongji.icu"
        self.api_base = f"{self.base_url}/api"
        self.console = Console()
        self.cookie_manager = CookieManager()
        self.session = None
        self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

        if self.session:
            try:
                self.session.close()
            except:
                pass
            self.session = None

    def create_session(self, cookies: Dict[str, str]) -> requests.Session:
        """创建带认证的session"""
        session = requests.Session()
        session.cookies.update(cookies)

        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            }
        )

        return session

    def test_cookie_authentication(self, cookies: Dict[str, str]) -> bool:
        """测试Cookie认证是否有效"""
        try:
            session = self.create_session(cookies)

            # 测试多个API端点
            test_endpoints = [
                "/api/me/",
                "/api/course/?page=1&page_size=1",
                "/api/review/?page=1&page_size=1",
            ]

            for endpoint in test_endpoints:
                response = session.get(self.base_url + endpoint, timeout=10)
                if response.status_code != 200:
                    self.console.print(
                        f"[yellow]API测试失败: {endpoint} -> {response.status_code}[/yellow]"
                    )
                    return False

            self.console.print("[green]✅ Cookie认证有效[/green]")
            self.session = session
            return True

        except Exception as e:
            self.console.print(f"[red]❌ Cookie认证测试失败: {e}[/red]")
            return False

    def init_selenium_driver(self) -> webdriver.Chrome:
        """初始化Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 无头模式
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        )

        # 反检测设置
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # 移除自动化标识
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        driver.implicitly_wait(10)
        driver.set_page_load_timeout(30)

        return driver

    def bypass_cloudflare_selenium(self) -> Optional[Dict[str, str]]:
        """使用Selenium绕过CloudFlare并获取Cookies"""
        try:
            self.console.print("[cyan]🔄 使用Selenium绕过CloudFlare...[/cyan]")

            self.driver = self.init_selenium_driver()
            self.driver.get(self.base_url)

            # 等待页面加载并检测CloudFlare
            time.sleep(5)

            # 检查CloudFlare指示器
            cloudflare_indicators = [
                "checking your browser",
                "cloudflare",
                "cf-wrapper",
                "cf-browser-verification",
                "challenge-form",
            ]

            page_source = self.driver.page_source.lower()
            has_cloudflare = any(
                indicator in page_source for indicator in cloudflare_indicators
            )

            if has_cloudflare:
                self.console.print(
                    "[yellow]🛡️  检测到CloudFlare验证，等待通过...[/yellow]"
                )

                # 等待CloudFlare验证完成（最多等待60秒）
                wait = WebDriverWait(self.driver, 60)
                wait.until(
                    lambda driver: not any(
                        indicator in driver.page_source.lower()
                        for indicator in cloudflare_indicators
                    )
                )

                self.console.print("[green]✅ CloudFlare验证通过[/green]")
                time.sleep(3)  # 额外等待

            # 尝试访问API来验证是否真正可用
            try:
                self.driver.get(f"{self.base_url}/api/course/?page=1&page_size=1")
                time.sleep(2)

                # 检查是否返回JSON数据
                page_text = self.driver.page_source
                if '"results"' in page_text or '"count"' in page_text:
                    # 获取cookies
                    selenium_cookies = self.driver.get_cookies()
                    cookies = {
                        cookie["name"]: cookie["value"] for cookie in selenium_cookies
                    }

                    self.console.print(
                        f"[green]✅ 成功获取 {len(cookies)} 个Cookies[/green]"
                    )

                    # 保存cookies
                    self.cookie_manager.save_cookies(cookies, "selenium_cloudflare")

                    return cookies
                else:
                    self.console.print("[red]❌ API仍无法访问[/red]")

            except Exception as e:
                self.console.print(f"[red]❌ API访问测试失败: {e}[/red]")

            return None

        except Exception as e:
            self.console.print(f"[red]❌ Selenium绕过失败: {e}[/red]")
            return None

    def try_cloudscraper(self) -> Optional[Dict[str, str]]:
        """尝试使用CloudScraper绕过"""
        try:
            self.console.print("[cyan]🔄 尝试CloudScraper绕过...[/cyan]")

            scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "linux", "mobile": False}
            )

            # 先访问主页
            response = scraper.get(self.base_url, timeout=30)
            if response.status_code == 200:
                # 测试API访问
                api_response = scraper.get(
                    f"{self.api_base}/course/?page=1&page_size=1", timeout=30
                )
                if api_response.status_code == 200:
                    cookies = dict(scraper.cookies)
                    self.console.print(
                        f"[green]✅ CloudScraper成功，获取 {len(cookies)} 个Cookies[/green]"
                    )

                    # 保存cookies
                    self.cookie_manager.save_cookies(cookies, "cloudscraper")

                    return cookies

            self.console.print("[yellow]⚠️  CloudScraper无法绕过[/yellow]")
            return None

        except Exception as e:
            self.console.print(f"[red]❌ CloudScraper失败: {e}[/red]")
            return None

    def authenticate(
        self, cookie_string: Optional[str] = None, force_refresh: bool = False
    ) -> bool:
        """
        主认证方法

        Args:
            cookie_string: 手动提供的Cookie字符串
            force_refresh: 强制刷新Cookie（忽略缓存）

        Returns:
            bool: 认证是否成功
        """
        self.console.print("[bold blue]🔐 开始认证过程...[/bold blue]")

        cookies = None

        # 1. 如果提供了Cookie字符串，优先使用
        if cookie_string:
            self.console.print("[cyan]📋 使用提供的Cookie字符串[/cyan]")
            cookies = self.cookie_manager.parse_cookie_string(cookie_string)
            if self.test_cookie_authentication(cookies):
                self.cookie_manager.save_cookies(cookies, "manual_input")
                return True
            else:
                self.console.print("[yellow]⚠️  提供的Cookie无效[/yellow]")

        # 2. 如果不强制刷新，尝试加载缓存的cookies
        if not force_refresh:
            self.console.print("[cyan]📁 尝试加载缓存Cookies[/cyan]")
            cookies = self.cookie_manager.load_cookies()
            if cookies and self.test_cookie_authentication(cookies):
                return True
            else:
                self.console.print("[yellow]⚠️  缓存的Cookies无效或已过期[/yellow]")

        # 3. 尝试使用CloudScraper自动获取
        cookies = self.try_cloudscraper()
        if cookies and self.test_cookie_authentication(cookies):
            return True

        # 4. 使用Selenium绕过CloudFlare
        cookies = self.bypass_cloudflare_selenium()
        if cookies and self.test_cookie_authentication(cookies):
            return True

        self.console.print("[red]❌ 所有认证方法都失败了[/red]")
        return False

    def get_session(self) -> Optional[requests.Session]:
        """获取认证后的session"""
        return self.session

    def refresh_cookies(self) -> bool:
        """刷新cookies"""
        return self.authenticate(force_refresh=True)