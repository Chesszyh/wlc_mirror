import time
import requests
from rich.console import Console
from typing import Any, Dict, Optional
from urllib.parse import urlencode


class TongjiAPIClient:
    """同济课程评价网站API客户端"""

    def __init__(self, cookies: Optional[Dict[str, str]] = None):
        """
        初始化API客户端

        Args:
            cookies: 认证cookie字典
        """
        self.base_url = "https://1.tongji.icu"
        self.api_base = f"{self.base_url}/api"
        self.console = Console()

        # 创建session
        self.session = requests.Session()
        if cookies:
            self.session.cookies.update(cookies)

        # 设置请求头
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": f"{self.base_url}/",
                "Origin": self.base_url,
            }
        )

        # 统计信息
        self.request_count = 0
        self.start_time = time.time()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发送HTTP请求"""
        url = f"{self.api_base}{endpoint}"
        self.request_count += 1

        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]请求失败: {method} {endpoint} - {e}[/red]")
            raise

    def test_authentication(self) -> bool:
        """测试API认证"""
        try:
            response = self._make_request("GET", "/me/")
            if response.status_code == 200:
                user_info = response.json()
                self.console.print(f"[green]✅ 认证成功[/green]")
                self.console.print(f"用户信息: {user_info}")
                return True
        except Exception as e:
            self.console.print(f"[red]❌ 认证失败: {e}[/red]")
        return False

    # === 用户相关API ===

    def get_user_info(self) -> Dict[str, Any]:
        """获取当前用户信息"""
        response = self._make_request("GET", "/me/")
        return response.json()

    def get_user_points(self) -> Dict[str, Any]:
        """获取用户积分信息"""
        response = self._make_request("GET", "/points/")
        return response.json()

    # === 课程相关API ===

    def get_courses(
        self, page: int = 1, page_size: int = 20, **filters
    ) -> Dict[str, Any]:
        """
        获取课程列表

        Args:
            page: 页码
            page_size: 每页大小
            **filters: 筛选条件
                - categories: 课程类别ID列表
                - department: 院系ID列表
                - notification_level: 通知级别
                - onlyhasreviews: 只显示有评价的课程
        """
        params = {"page": page, "page_size": page_size, **filters}
        endpoint = f"/course/?{urlencode(params, doseq=True)}"
        response = self._make_request("GET", endpoint)
        return response.json()

    def get_course_detail(self, course_id: int) -> Dict[str, Any]:
        """获取课程详细信息"""
        response = self._make_request("GET", f"/course/{course_id}/")
        return response.json()

    def search_courses(
        self, query: str, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        搜索课程

        Args:
            query: 搜索关键词（课程名、课号、教师名等）
            page: 页码
            page_size: 每页大小
        """
        params = {"q": query, "page": page, "page_size": page_size}
        endpoint = f"/search/?{urlencode(params)}"
        response = self._make_request("GET", endpoint)
        return response.json()

    def get_course_filter_options(self) -> Dict[str, Any]:
        """获取课程筛选选项（院系、类别等）"""
        response = self._make_request("GET", "/course-filter/")
        return response.json()

    # === 评价相关API ===

    def get_reviews(
        self, page: int = 1, page_size: int = 20, **filters
    ) -> Dict[str, Any]:
        """
        获取评价列表

        Args:
            page: 页码
            page_size: 每页大小
            **filters: 筛选条件
                - order: 排序方式 ('approves' 按赞数排序)
                - notification_level: 通知级别
        """
        params = {"page": page, "page_size": page_size, **filters}
        endpoint = f"/review/?{urlencode(params)}"
        response = self._make_request("GET", endpoint)
        return response.json()

    def get_review_detail(self, review_id: int) -> Dict[str, Any]:
        """获取评价详细信息"""
        response = self._make_request("GET", f"/review/{review_id}/")
        return response.json()

    def get_course_reviews(
        self, course_id: int, page: int = 1, page_size: int = 20, **filters
    ) -> Dict[str, Any]:
        """
        获取指定课程的评价

        Args:
            course_id: 课程ID
            page: 页码
            page_size: 每页大小
            **filters: 筛选条件
                - order: 排序方式 (0-最新发表, 1-最早发表, 2-获赞从高到低, 3-推荐指数从高到低, 4-推荐指数从低到高)
                - semester: 学期ID
                - rating: 评分筛选
        """
        params = {"page": page, "page_size": page_size, **filters}
        endpoint = f"/course/{course_id}/review/?{urlencode(params)}"
        response = self._make_request("GET", endpoint)
        return response.json()

    def get_review_filter_options(self) -> Dict[str, Any]:
        """获取评价筛选选项"""
        response = self._make_request("GET", "/review-filter/")
        return response.json()

    # === 基础数据API ===

    def get_semesters(self) -> Dict[str, Any]:
        """获取学期列表"""
        response = self._make_request("GET", "/semester/")
        return response.json()

    def get_announcements(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取公告列表"""
        params = {"page": page, "page_size": page_size}
        endpoint = f"/announcement/?{urlencode(params)}"
        response = self._make_request("GET", endpoint)
        return response.json()

    def get_statistics(self) -> Dict[str, Any]:
        """获取网站统计信息"""
        response = self._make_request("GET", "/statistic/")
        return response.json()

    def get_common_info(self) -> Dict[str, Any]:
        """获取通用信息"""
        response = self._make_request("GET", "/common/")
        return response.json()
