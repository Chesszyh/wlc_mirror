#!/usr/bin/env python3
"""
同济课程评价网站完整数据同步脚本
整合cookie认证、API调用、数据采集功能

使用方法:
python complete_sync.py --mode full --output data.json
python complete_sync.py --mode incremental --last-sync 2024-01-01
python complete_sync.py --test-only
"""

import argparse
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table
from rich import print as rprint

# 导入我们之前创建的模块
from api_client import TongjiAPIClient


class CompleteSyncManager:
    """完整数据同步管理器"""

    def __init__(self, output_dir: str = "sync_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.console = Console()
        self.logger = self._setup_logging()

        # 统计信息
        self.stats = {
            "start_time": None,
            "end_time": None,
            "total_requests": 0,
            "courses_collected": 0,
            "reviews_collected": 0,
            "teachers_collected": 0,
            "departments_collected": 0,
            "errors": [],
        }

    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        log_file = (
            self.output_dir / f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )

        return logging.getLogger(__name__)

    def authenticate(
        self, cookie_string: Optional[str] = None
    ) -> Optional[TongjiAPIClient]:
        """认证并创建API客户端"""
        self.console.print("[bold blue]🔐 开始认证...[/bold blue]")

        try:
            with TongjiAuthenticator() as auth:
                if auth.authenticate(cookie_string):
                    session = auth.get_session()
                    if session:
                        # 从session的cookies创建API客户端
                        cookies = dict(session.cookies)
                        client = TongjiAPIClient(cookies)

                        # 测试API客户端
                        if client.test_authentication():
                            self.console.print("[green]✅ API客户端创建成功[/green]")
                            return client

            self.console.print("[red]❌ 认证失败[/red]")
            return None

        except Exception as e:
            self.logger.error(f"认证过程出错: {e}")
            self.console.print(f"[red]❌ 认证异常: {e}[/red]")
            return None

    def collect_base_data(self, client: TongjiAPIClient) -> Dict[str, Any]:
        """采集基础数据（院系、学期、类别等）"""
        self.console.print("[cyan]📊 采集基础数据...[/cyan]")
        base_data = {}

        try:
            # 院系和类别数据
            filter_options = client.get_course_filter_options()
            base_data["departments"] = filter_options.get("departments", [])
            base_data["categories"] = filter_options.get("categories", [])

            # 学期数据
            semesters_response = client.get_semesters()
            if isinstance(semesters_response, dict):
                base_data["semesters"] = semesters_response.get("results", [])
            else:
                base_data["semesters"] = (
                    semesters_response if isinstance(semesters_response, list) else []
                )

            # 统计信息
            base_data["statistics"] = client.get_statistics()

            # 公告信息
            announcements_response = client.get_announcements(page_size=50)
            if isinstance(announcements_response, dict):
                base_data["announcements"] = announcements_response.get("results", [])
            else:
                base_data["announcements"] = (
                    announcements_response
                    if isinstance(announcements_response, list)
                    else []
                )

            self.stats["departments_collected"] = len(base_data["departments"])

            self.console.print(f"[green]✅ 基础数据采集完成[/green]")
            self.console.print(f"  - 院系: {len(base_data['departments'])} 个")
            self.console.print(f"  - 类别: {len(base_data['categories'])} 个")
            self.console.print(f"  - 学期: {len(base_data['semesters'])} 个")

            return base_data

        except Exception as e:
            self.logger.error(f"采集基础数据失败: {e}")
            self.stats["errors"].append(f"基础数据采集: {e}")
            return {}

    def collect_courses_data(
        self, client: TongjiAPIClient, max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """采集课程数据"""
        self.console.print("[cyan]📚 采集课程数据...[/cyan]")

        all_courses = []
        page = 1

        with Progress() as progress:
            task = progress.add_task("[cyan]采集课程...", total=None)

            while True:
                if max_pages and page > max_pages:
                    break

                try:
                    data = client.get_courses(page=page, page_size=100)
                    courses = data.get("results", [])

                    if not courses:
                        break

                    all_courses.extend(courses)
                    self.stats["courses_collected"] = len(all_courses)
                    self.stats["total_requests"] += 1

                    progress.update(
                        task,
                        description=f"[cyan]已采集 {len(all_courses)} 门课程（第{page}页）...",
                    )

                    if not data.get("next"):
                        break

                    page += 1
                    time.sleep(0.3)  # 控制请求频率

                except Exception as e:
                    self.logger.error(f"采集课程第{page}页失败: {e}")
                    self.stats["errors"].append(f"课程第{page}页: {e}")
                    break

        self.console.print(f"[green]✅ 课程数据采集完成: {len(all_courses)} 门[/green]")
        return all_courses

    def collect_reviews_data(
        self,
        client: TongjiAPIClient,
        courses: Optional[List[Dict[str, Any]]] = None,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """采集评价数据"""
        self.console.print("[cyan]💬 采集评价数据...[/cyan]")

        all_reviews = []

        if courses:
            # 按课程采集评价
            course_ids = [
                course["id"] for course in courses if course.get("review_count", 0) > 0
            ]

            with Progress() as progress:
                task = progress.add_task("[cyan]采集评价...", total=len(course_ids))

                for i, course_id in enumerate(course_ids):
                    try:
                        page = 1
                        course_reviews = []

                        while True:
                            if max_pages and page > max_pages:
                                break

                            data = client.get_course_reviews(
                                course_id, page=page, page_size=100
                            )
                            reviews = data.get("results", [])

                            if not reviews:
                                break

                            course_reviews.extend(reviews)
                            self.stats["total_requests"] += 1

                            if not data.get("next"):
                                break

                            page += 1
                            time.sleep(0.2)

                        all_reviews.extend(course_reviews)
                        self.stats["reviews_collected"] = len(all_reviews)

                        progress.update(
                            task,
                            advance=1,
                            description=f"[cyan]已采集 {len(all_reviews)} 条评价 ({i+1}/{len(course_ids)})...",
                        )

                    except Exception as e:
                        self.logger.error(f"采集课程 {course_id} 评价失败: {e}")
                        self.stats["errors"].append(f"课程{course_id}评价: {e}")

        else:
            # 采集所有评价
            page = 1

            with Progress() as progress:
                task = progress.add_task("[cyan]采集评价...", total=None)

                while True:
                    if max_pages and page > max_pages:
                        break

                    try:
                        data = client.get_reviews(page=page, page_size=100)
                        reviews = data.get("results", [])

                        if not reviews:
                            break

                        all_reviews.extend(reviews)
                        self.stats["reviews_collected"] = len(all_reviews)
                        self.stats["total_requests"] += 1

                        progress.update(
                            task,
                            description=f"[cyan]已采集 {len(all_reviews)} 条评价（第{page}页）...",
                        )

                        if not data.get("next"):
                            break

                        page += 1
                        time.sleep(0.3)

                    except Exception as e:
                        self.logger.error(f"采集评价第{page}页失败: {e}")
                        self.stats["errors"].append(f"评价第{page}页: {e}")
                        break

        self.console.print(f"[green]✅ 评价数据采集完成: {len(all_reviews)} 条[/green]")
        return all_reviews

    def extract_teachers_data(
        self, courses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """从课程数据中提取教师信息"""
        teachers_map = {}

        for course in courses:
            # 主讲教师
            main_teacher = course.get("main_teacher")
            if main_teacher and isinstance(main_teacher, dict):
                teacher_id = main_teacher.get("id")
                if teacher_id and teacher_id not in teachers_map:
                    teachers_map[teacher_id] = main_teacher

            # 教师组成
            teacher_group = course.get("teacher_group", [])
            for teacher in teacher_group:
                if isinstance(teacher, dict):
                    teacher_id = teacher.get("id")
                    if teacher_id and teacher_id not in teachers_map:
                        teachers_map[teacher_id] = teacher

        teachers = list(teachers_map.values())
        self.stats["teachers_collected"] = len(teachers)

        self.console.print(f"[green]✅ 提取教师信息: {len(teachers)} 位[/green]")
        return teachers

    def analyze_and_enrich_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析和丰富数据"""
        self.console.print("[cyan]📈 分析数据...[/cyan]")

        courses = data.get("courses", [])
        reviews = data.get("reviews", [])

        # 添加分析数据
        analysis = {
            "summary": {
                "total_courses": len(courses),
                "total_reviews": len(reviews),
                "total_teachers": len(data.get("teachers", [])),
                "total_departments": len(
                    data.get("base_data", {}).get("departments", [])
                ),
                "avg_reviews_per_course": len(reviews) / len(courses) if courses else 0,
                "collection_date": datetime.now().isoformat(),
                "collection_stats": self.stats,
            },
            "department_stats": {},
            "rating_distribution": {},
            "teacher_stats": {},
            "semester_stats": {},
        }

        # 院系统计
        for course in courses:
            dept = course.get("department", {})
            dept_name = dept.get("name", "未知院系") if dept else "未知院系"
            if dept_name not in analysis["department_stats"]:
                analysis["department_stats"][dept_name] = {
                    "course_count": 0,
                    "total_reviews": 0,
                    "avg_rating": 0,
                }

            analysis["department_stats"][dept_name]["course_count"] += 1
            analysis["department_stats"][dept_name]["total_reviews"] += course.get(
                "review_count", 0
            )

        # 评分分布统计
        rating_counts = [0] * 6  # 0-5分
        for review in reviews:
            rating = review.get("rating", 0)
            if 0 <= rating <= 5:
                rating_counts[rating] += 1

        analysis["rating_distribution"] = {f"{i}星": rating_counts[i] for i in range(6)}

        # 学期统计
        for review in reviews:
            semester = review.get("semester", {})
            semester_name = semester.get("name", "未知学期") if semester else "未知学期"
            if semester_name not in analysis["semester_stats"]:
                analysis["semester_stats"][semester_name] = 0
            analysis["semester_stats"][semester_name] += 1

        data["analysis"] = analysis

        self.console.print("[green]✅ 数据分析完成[/green]")
        return data

    def save_data(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """保存数据到文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tongji_complete_data_{timestamp}.json"

        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.console.print(f"[green]💾 数据已保存到: {filepath}[/green]")
        self.logger.info(f"数据保存到: {filepath}")

        return str(filepath)

    def display_summary(self, data: Dict[str, Any]):
        """显示同步摘要"""
        self.console.print("\n[bold blue]📋 同步摘要报告[/bold blue]")

        analysis = data.get("analysis", {})
        summary = analysis.get("summary", {})

        # 基本统计表
        stats_table = Table(
            title="数据统计", show_header=True, header_style="bold magenta"
        )
        stats_table.add_column("项目", style="cyan")
        stats_table.add_column("数量", style="green")

        stats_table.add_row("课程总数", str(summary.get("total_courses", 0)))
        stats_table.add_row("评价总数", str(summary.get("total_reviews", 0)))
        stats_table.add_row("教师总数", str(summary.get("total_teachers", 0)))
        stats_table.add_row("院系总数", str(summary.get("total_departments", 0)))
        stats_table.add_row(
            "平均每门课评价数", f"{summary.get('avg_reviews_per_course', 0):.1f}"
        )
        stats_table.add_row("API请求次数", str(self.stats["total_requests"]))

        if self.stats["start_time"] and self.stats["end_time"]:
            duration = self.stats["end_time"] - self.stats["start_time"]
            stats_table.add_row("同步耗时", str(duration).split(".")[0])

        self.console.print(stats_table)

        # 评分分布
        rating_dist = analysis.get("rating_distribution", {})
        if rating_dist:
            rating_table = Table(
                title="评分分布", show_header=True, header_style="bold magenta"
            )
            rating_table.add_column("评分", style="cyan")
            rating_table.add_column("数量", style="green")
            rating_table.add_column("占比", style="yellow")

            total_reviews = sum(rating_dist.values())
            for rating, count in rating_dist.items():
                percentage = (
                    f"{count/total_reviews*100:.1f}%" if total_reviews > 0 else "0%"
                )
                rating_table.add_row(rating, str(count), percentage)

            self.console.print(rating_table)

        # 错误报告
        if self.stats["errors"]:
            self.console.print("\n[bold red]⚠️  错误报告[/bold red]")
            for error in self.stats["errors"]:
                self.console.print(f"[red]• {error}[/red]")

    def run_full_sync(
        self, cookie_string: Optional[str] = None, max_pages: Optional[int] = None
    ) -> Optional[str]:
        """执行完整同步"""
        self.stats["start_time"] = datetime.now()
        self.console.print("[bold green]🚀 开始完整数据同步[/bold green]")

        try:
            # 1. 认证
            client = self.authenticate(cookie_string)
            if not client:
                return None

            # 2. 采集基础数据
            base_data = self.collect_base_data(client)

            # 3. 采集课程数据
            courses = self.collect_courses_data(client, max_pages)

            # 4. 采集评价数据
            reviews = self.collect_reviews_data(client, courses, max_pages)

            # 5. 提取教师数据
            teachers = self.extract_teachers_data(courses)

            # 6. 整合所有数据
            complete_data = {
                "base_data": base_data,
                "courses": courses,
                "reviews": reviews,
                "teachers": teachers,
                "metadata": {
                    "sync_type": "full",
                    "sync_time": datetime.now().isoformat(),
                    "tool_version": "1.0.0",
                    "source_url": "https://1.tongji.icu",
                },
            }

            # 7. 分析和丰富数据
            complete_data = self.analyze_and_enrich_data(complete_data)

            # 8. 保存数据
            filepath = self.save_data(complete_data)

            # 9. 显示摘要
            self.stats["end_time"] = datetime.now()
            self.display_summary(complete_data)

            self.console.print("[bold green]🎉 完整同步成功完成！[/bold green]")
            return filepath

        except Exception as e:
            self.logger.error(f"完整同步失败: {e}")
            self.console.print(f"[red]💥 同步失败: {e}[/red]")
            return None

    def test_connection(self, cookie_string: Optional[str] = None) -> bool:
        """测试连接"""
        self.console.print("[cyan]🔍 测试API连接...[/cyan]")

        client = self.authenticate(cookie_string)
        if not client:
            return False

        try:
            # 测试各种API端点
            test_results = {}

            # 用户信息
            try:
                user_info = client.get_user_info()
                test_results["user_info"] = "✅ 成功"
                self.console.print(f"用户信息: {user_info.get('username', 'Unknown')}")
            except:
                test_results["user_info"] = "❌ 失败"

            # 课程列表
            try:
                courses = client.get_courses(page_size=1)
                test_results["courses"] = (
                    "✅ 成功" if courses.get("results") else "❌ 无数据"
                )
            except:
                test_results["courses"] = "❌ 失败"

            # 评价列表
            try:
                reviews = client.get_reviews(page_size=1)
                test_results["reviews"] = (
                    "✅ 成功" if reviews.get("results") else "❌ 无数据"
                )
            except:
                test_results["reviews"] = "❌ 失败"

            # 搜索功能
            try:
                search_results = client.search_courses("高等数学", page_size=1)
                test_results["search"] = (
                    "✅ 成功" if search_results.get("results") else "❌ 无数据"
                )
            except:
                test_results["search"] = "❌ 失败"

            # 显示测试结果
            test_table = Table(title="API测试结果")
            test_table.add_column("API端点", style="cyan")
            test_table.add_column("状态", style="green")

            for endpoint, status in test_results.items():
                test_table.add_row(endpoint, status)

            self.console.print(test_table)

            # 判断整体成功
            success_count = sum(
                1 for status in test_results.values() if "成功" in status
            )
            total_count = len(test_results)

            if success_count == total_count:
                self.console.print("[green]🎉 所有API测试通过！[/green]")
                return True
            else:
                self.console.print(
                    f"[yellow]⚠️  {success_count}/{total_count} 个API测试通过[/yellow]"
                )
                return success_count > 0

        except Exception as e:
            self.console.print(f"[red]❌ 连接测试失败: {e}[/red]")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="同济课程评价网站数据同步工具")
    parser.add_argument(
        "--mode",
        choices=["full", "test"],
        default="full",
        help="同步模式: full=完整同步, test=测试连接",
    )
    parser.add_argument("--cookie", type=str, help="Cookie字符串")
    parser.add_argument("--output", type=str, help="输出文件名")
    parser.add_argument("--max-pages", type=int, help="最大页数限制（用于测试）")
    parser.add_argument("--output-dir", type=str, default="sync_data", help="输出目录")

    args = parser.parse_args()

    # 创建同步管理器
    sync_manager = CompleteSyncManager(args.output_dir)

    if args.mode == "test":
        # 测试模式
        success = sync_manager.test_connection(args.cookie)
        exit(0 if success else 1)

    elif args.mode == "full":
        # 完整同步模式
        result = sync_manager.run_full_sync(args.cookie, args.max_pages)
        exit(0 if result else 1)


if __name__ == "__main__":
    main()
