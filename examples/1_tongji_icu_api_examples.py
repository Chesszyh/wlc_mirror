#!/usr/bin/env python3
"""
tongji.icu API调用示例
基于cookie认证，全面展示1.tongji.icu的API功能

该示例展示了如何：
1. 使用cookie认证访问API
2. 获取各类数据（课程、评价、院系等）
3. 搜索和筛选功能
4. 数据分析和统计
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich import print as rprint


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

    # === 数据采集和分析方法 ===

    def collect_all_courses(
        self, max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """采集所有课程数据"""
        all_courses = []
        page = 1

        with Progress() as progress:
            task = progress.add_task("[cyan]采集课程数据...", total=None)

            while True:
                if max_pages and page > max_pages:
                    break

                try:
                    data = self.get_courses(page=page, page_size=100)
                    courses = data.get("results", [])

                    if not courses:
                        break

                    all_courses.extend(courses)
                    progress.update(
                        task,
                        description=f"[cyan]已采集 {len(all_courses)} 门课程（第{page}页）...",
                    )

                    if not data.get("next"):
                        break

                    page += 1
                    time.sleep(0.5)  # 控制请求频率

                except Exception as e:
                    self.console.print(f"[red]采集第{page}页失败: {e}[/red]")
                    break

        self.console.print(f"[green]课程采集完成，总计: {len(all_courses)} 门[/green]")
        return all_courses

    def collect_all_reviews(
        self, max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """采集所有评价数据"""
        all_reviews = []
        page = 1

        with Progress() as progress:
            task = progress.add_task("[cyan]采集评价数据...", total=None)

            while True:
                if max_pages and page > max_pages:
                    break

                try:
                    data = self.get_reviews(page=page, page_size=100)
                    reviews = data.get("results", [])

                    if not reviews:
                        break

                    all_reviews.extend(reviews)
                    progress.update(
                        task,
                        description=f"[cyan]已采集 {len(all_reviews)} 条评价（第{page}页）...",
                    )

                    if not data.get("next"):
                        break

                    page += 1
                    time.sleep(0.5)  # 控制请求频率

                except Exception as e:
                    self.console.print(f"[red]采集第{page}页失败: {e}[/red]")
                    break

        self.console.print(f"[green]评价采集完成，总计: {len(all_reviews)} 条[/green]")
        return all_reviews

    def analyze_course_data(self, courses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析课程数据"""
        analysis = {
            "total_courses": len(courses),
            "departments": {},
            "categories": {},
            "credits": {},
            "rating_stats": {
                "high_rated": 0,  # >4.0
                "medium_rated": 0,  # 3.0-4.0
                "low_rated": 0,  # <3.0
                "no_rating": 0,
            },
        }

        for course in courses:
            # 院系统计
            dept = course.get("department", {})
            if isinstance(dept, dict):
                dept_name = dept.get("name", "未知院系")
            elif isinstance(dept, str):
                dept_name = dept
            else:
                dept_name = "未知院系"
            analysis["departments"][dept_name] = (
                analysis["departments"].get(dept_name, 0) + 1
            )

            # 类别统计
            categories = course.get("categories", [])
            for cat in categories:
                analysis["categories"][cat] = (
                    analysis["categories"].get(cat, 0) + 1
                )

            # 学分统计
            credit = course.get("credit", 0)
            analysis["credits"][credit] = analysis["credits"].get(credit, 0) + 1

            # 评分统计
            avg_rating = course.get("review_avg")
            if avg_rating is None or avg_rating == 0:
                analysis["rating_stats"]["no_rating"] += 1
            elif avg_rating >= 4.0:
                analysis["rating_stats"]["high_rated"] += 1
            elif avg_rating >= 3.0:
                analysis["rating_stats"]["medium_rated"] += 1
            else:
                analysis["rating_stats"]["low_rated"] += 1

        return analysis

    def display_data_summary(
        self, courses: List[Dict[str, Any]], reviews: List[Dict[str, Any]]
    ):
        """显示数据摘要"""
        self.console.print("\n[bold blue]📊 数据采集摘要[/bold blue]")

        # 基本统计
        stats_table = Table(title="基本统计")
        stats_table.add_column("项目", style="cyan")
        stats_table.add_column("数量", style="magenta")

        stats_table.add_row("课程总数", str(len(courses)))
        stats_table.add_row("评价总数", str(len(reviews)))
        stats_table.add_row("API请求次数", str(self.request_count))
        stats_table.add_row("耗时", f"{time.time() - self.start_time:.2f}秒")

        self.console.print(stats_table)

        # 课程分析
        if courses:
            analysis = self.analyze_course_data(courses)

            # 院系分布
            dept_table = Table(title="院系分布 Top 10")
            dept_table.add_column("院系", style="cyan")
            dept_table.add_column("课程数", style="magenta")

            top_depts = sorted(
                analysis["departments"].items(), key=lambda x: x[1], reverse=True
            )[:10]
            for dept, count in top_depts:
                dept_table.add_row(dept, str(count))

            self.console.print(dept_table)

            # 评分分布
            rating_table = Table(title="课程评分分布")
            rating_table.add_column("评分段", style="cyan")
            rating_table.add_column("课程数", style="magenta")
            rating_table.add_column("占比", style="green")

            total = analysis["total_courses"]
            rating_stats = analysis["rating_stats"]
            for level, count in rating_stats.items():
                pct = f"{count/total*100:.1f}%" if total > 0 else "0%"
                level_name = {
                    "high_rated": "高分课程 (≥4.0)",
                    "medium_rated": "中等课程 (3.0-4.0)",
                    "low_rated": "低分课程 (<3.0)",
                    "no_rating": "暂无评价",
                }.get(level, level)
                rating_table.add_row(level_name, str(count), pct)

            self.console.print(rating_table)

    def display_courses_reviews(self, course: Dict[str, Any]):
        if course:
          teacher_name = course.get("teacher", "未知教师")
          rating = course.get("rating")
          if rating:
              review_count = rating.get("count") or 0
              review_avg = rating.get("avg") or 0.0
          else:
              review_count = 0
              review_avg = 0.0
          self.console.print(
              f"  • {course.get('code')} {course.get('name')} - {teacher_name} (平均评分: {review_avg:.1f}, 评价: {review_count}条)"
          )
        else:
            self.console.print("  未找到相关课程")

    def demo_search_examples(self):
        """演示搜索功能示例"""
        self.console.print("\n[bold blue]🔍 搜索功能演示[/bold blue]")
        search_terms = ["沈坚"] # "高等数学", "计算机", "英语", "物理"
        for term in search_terms:
            try:
                response = self.search_courses(term, page_size=5)
                self.console.print(f"\n搜索 '{term}' 的结果:")
                results = response.get("results", [])
                for course in results if isinstance(results, list) else []:
                    self.display_courses_reviews(course)

            except Exception as e:
                self.console.print(f"  [red]搜索失败: {e}[/red]")

    def demo_course_reviews(self, course_id: Optional[int] = None):
        """演示课程评价查看"""
        if not course_id:
            # 先找一个有评价的课程
            courses_data = self.get_courses(onlyhasreviews="avg", page_size=5)
            courses = courses_data.get("results", [])
            if not courses:
                self.console.print("[yellow]没有找到有评价的课程[/yellow]")
                return
            course_id = courses[0]["id"]

        if course_id is None:
            return

        self.console.print(
            f"\n[bold blue]📝 课程评价演示 (课程ID: {course_id})[/bold blue]"
        )

        try:
            # 获取课程详情
            course = self.get_course_detail(course_id)
            self.console.print(f"课程: {course.get('code')} {course.get('name')}")

            # 获取评价
            reviews_data = self.get_course_reviews(
                course_id, page_size=5, order=3
            )  # 按推荐指数排序
            reviews = reviews_data.get("results", [])

            if reviews:
                review_table = Table(title="课程评价")
                review_table.add_column("评分", style="cyan")
                review_table.add_column("学期", style="magenta")
                review_table.add_column("评价摘要", style="green")
                review_table.add_column("赞数", style="yellow")
                review_table.add_column("踩数", style="red")

                for review in reviews:
                    rating = "⭐" * review.get("rating", 0)
                    semester = review.get("semester", "未知学期")
                    comment = review.get("comment", "")
                    reaction = review.get("reactions", {})
                    approves = reaction.get("approves", 0)
                    disapproves = reaction.get("disapproves", 0)
                    review_table.add_row(rating, semester, comment, str(approves), str(disapproves))
                self.console.print(review_table)

            else:
                self.console.print("该课程暂无评价")

        except Exception as e:
            self.console.print(f"[red]获取课程评价失败: {e}[/red]")


def create_client_from_cookie_string(cookie_string: str) -> TongjiAPIClient:
    """从Cookie字符串创建API客户端"""
    cookies = {}
    for item in cookie_string.split(";"):
        if "=" in item:
            key, value = item.strip().split("=", 1)
            cookies[key] = value
    return TongjiAPIClient(cookies=cookies)


def main():
    """主演示函数"""
    console = Console()
    console.print("[bold green]🎓 tongji.icu API 调用演示[/bold green]")

    # 从/cookies.ini读取
    with open("cookies.ini", "r", encoding="utf-8") as f:
        lines = f.readlines()
    cookie_string = "; ".join(line.strip() for line in lines)
    # rprint(f"使用的Cookie字符串: {cookie_string}")

    # 创建API客户端
    client = create_client_from_cookie_string(cookie_string)

    try:
        # 1. 测试认证
        if False:
          if not client.test_authentication():
              console.print("[red]Cookie认证失败，请检查Cookie是否有效[/red]")
              return
        else:
          console.print("\n[bold blue]📊 登录成功！[/bold blue]")

        # 2. 获取基础信息
        if False:
          console.print("\n[bold blue]📊 获取基础信息[/bold blue]")
          try:
              stats = client.get_statistics()
              console.print(f"网站统计: {stats}")

              filter_options = client.get_course_filter_options()
              departments = filter_options.get("departments", [])
              categories = filter_options.get("categories", [])
              console.print(f"院系数量: {len(departments)}")
              console.print(f"课程类别数量: {len(categories)}")
          except Exception as e:
              console.print(f"[yellow]获取基础信息失败: {e}[/yellow]")
          input("按回车键继续...")

        # 3. 演示搜索功能
        if False:
          client.demo_search_examples()
          input("按回车键继续...")

        # 4. 演示课程评价查看
        if False:
          client.demo_course_reviews()
          input("按回车键继续...")

        # 5. 采集数据样本
        if True:
          console.print("\n[bold blue]📁 采集数据样本[/bold blue]")
          courses = client.collect_all_courses(max_pages=1)  # 限制页数避免过长
          reviews = client.collect_all_reviews(max_pages=1)
          input("按回车键继续...")

          # 6. 显示数据摘要
          client.display_data_summary(courses, reviews)
          input("按回车键继续...")

          # 7. 保存数据样本
          timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

          with open(f"courses_sample_{timestamp}.json", "w", encoding="utf-8") as f:
              json.dump(courses, f, ensure_ascii=False, indent=2)

          with open(f"reviews_sample_{timestamp}.json", "w", encoding="utf-8") as f:
              json.dump(reviews, f, ensure_ascii=False, indent=2)

          console.print(f"\n[green]✅ 数据样本已保存到文件[/green]")
          console.print(f"- courses_sample_{timestamp}.json ({len(courses)} 门课程)")
          console.print(f"- reviews_sample_{timestamp}.json ({len(reviews)} 条评价)")

    except Exception as e:
        console.print(f"[red]演示过程中出错: {e}[/red]")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
