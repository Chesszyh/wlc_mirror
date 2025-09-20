#!/usr/bin/env python3
"""
tongji.icu 镜像站数据同步脚本

该脚本从原站API获取数据，并生成静态镜像站的数据文件。
支持增量更新、错误重试、详细日志记录。

"""
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import os
import sys
from dataclasses import dataclass, asdict, field
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from api_client import TongjiAPIClient
from auth import TongjiAuthenticator


@dataclass
class SyncConfig:
    """同步配置"""
    output_dir: Path = Path("docs")
    data_dir: Path = Path("docs/data")
    max_retry: int = 3
    retry_delay: float = 2.0
    request_delay: float = 0.5
    max_pages_per_endpoint: Optional[int] = None
    parallel_workers: int = 4
    incremental_update: bool = True
    force_full_sync: bool = False


@dataclass
class SyncStats:
    """同步统计信息"""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_courses: int = 0
    total_reviews: int = 0
    new_courses: int = 0
    updated_courses: int = 0
    new_reviews: int = 0
    updated_reviews: int = 0
    api_requests: int = 0
    failed_requests: int = 0
    errors: List[str] = field(default_factory=list)


class MirrorSiteSyncer:
    """镜像站同步器"""

    def __init__(self, config: Optional[SyncConfig] = None, cookie_string: Optional[str] = None):
        self.config = config or SyncConfig()
        self.stats = SyncStats(start_time=datetime.now(timezone.utc))
        self.lock = threading.Lock()

        # 设置日志
        self._setup_logging()

        # 初始化客户端
        self.client: Optional[TongjiAPIClient] = None
        self.cookie_string = cookie_string

        # 创建输出目录
        self._ensure_directories()

        # 加载现有数据
        self.existing_data = self._load_existing_data()

    def _setup_logging(self):
        """设置日志系统"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"sync_{timestamp}.log"

        # 配置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )

        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # 配置根日志器
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info(f"日志文件: {log_file}")

    def _ensure_directories(self):
        """确保输出目录存在"""
        directories = [
            self.config.output_dir,
            self.config.data_dir,
            self.config.data_dir / "courses",
            self.config.data_dir / "courses" / "details",
            self.config.data_dir / "courses" / "by-department",
            self.config.data_dir / "courses" / "by-category",
            self.config.data_dir / "reviews",
            self.config.data_dir / "reviews" / "by-course",
            self.config.data_dir / "reviews" / "latest",
            self.config.data_dir / "statistics",
            self.config.data_dir / "filters",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_existing_data(self) -> Dict[str, Any]:
        """加载现有数据用于增量更新"""
        existing_data = {
            "courses_index": {},
            "courses_details": {},
            "reviews_index": {},
            "last_sync": None,
            "metadata": {}
        }

        try:
            # 加载课程索引
            courses_index_file = self.config.data_dir / "courses" / "index.json"
            if courses_index_file.exists():
                with open(courses_index_file, 'r', encoding='utf-8') as f:
                    existing_data["courses_index"] = json.load(f)

            # 加载评价索引
            reviews_index_file = self.config.data_dir / "reviews" / "index.json"
            if reviews_index_file.exists():
                with open(reviews_index_file, 'r', encoding='utf-8') as f:
                    existing_data["reviews_index"] = json.load(f)

            # 加载同步元数据
            metadata_file = self.config.data_dir / "sync_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    existing_data["metadata"] = metadata
                    existing_data["last_sync"] = metadata.get("last_sync")

        except Exception as e:
            self.logger.warning(f"加载现有数据失败: {e}")

        return existing_data

    def _init_client(self) -> bool:
        """初始化API客户端"""
        try:
            # 尝试使用提供的cookie
            if self.cookie_string:
                cookies = {}
                for item in self.cookie_string.split(";"):
                    if "=" in item:
                        key, value = item.strip().split("=", 1)
                        cookies[key] = value
                self.client = TongjiAPIClient(cookies=cookies)

                if self.client.test_authentication():
                    self.logger.info("使用提供的Cookie认证成功")
                    return True
                else:
                    self.logger.warning("提供的Cookie认证失败")

            # 尝试自动认证
            with TongjiAuthenticator() as auth:
                if auth.authenticate():
                    session = auth.get_session()
                    self.client = TongjiAPIClient(cookies=dict(session.cookies))
                    self.logger.info("自动认证成功")
                    return True
                else:
                    self.logger.error("自动认证失败")
                    return False

        except Exception as e:
            self.logger.error(f"初始化客户端失败: {e}")
            return False

    def _make_request_with_retry(self, func, *args, **kwargs) -> Optional[Any]:
        """带重试的API请求"""
        if self.client is None:
            self.logger.error("API客户端未初始化")
            return None

        for attempt in range(self.config.max_retry):
            try:
                with self.lock:
                    self.stats.api_requests += 1

                result = func(*args, **kwargs)
                time.sleep(self.config.request_delay)
                return result

            except Exception as e:
                self.logger.warning(f"API请求失败 (尝试 {attempt + 1}/{self.config.max_retry}): {e}")

                with self.lock:
                    self.stats.failed_requests += 1

                if attempt < self.config.max_retry - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    self.logger.error(f"API请求最终失败: {func.__name__}")
                    self.stats.errors.append(f"API请求失败: {func.__name__} - {e}")

        return None

    def _collect_all_courses(self) -> List[Dict[str, Any]]:
        """采集所有课程数据"""
        self.logger.info("开始采集课程数据...")
        all_courses = []
        page = 1

        while True:
            if self.config.max_pages_per_endpoint and page > self.config.max_pages_per_endpoint:
                break

            if self.client is None:
                self.logger.error("API客户端未初始化")
                break

            data = self._make_request_with_retry(
                self.client.get_courses,
                page=page,
                page_size=100
            )

            if not data:
                break

            courses = data.get("results", [])
            if not courses:
                break

            all_courses.extend(courses)
            self.logger.info(f"采集课程数据第{page}页，累计: {len(all_courses)} 门课程")

            if not data.get("next"):
                break

            page += 1

        self.stats.total_courses = len(all_courses)
        self.logger.info(f"课程数据采集完成，总计: {len(all_courses)} 门课程")
        return all_courses

    def _collect_all_reviews(self) -> List[Dict[str, Any]]:
        """采集所有评价数据"""
        self.logger.info("开始采集评价数据...")
        all_reviews = []
        page = 1

        while True:
            if self.config.max_pages_per_endpoint and page > self.config.max_pages_per_endpoint:
                break

            if self.client is None:
                self.logger.error("API客户端未初始化")
                break

            data = self._make_request_with_retry(
                self.client.get_reviews,
                page=page,
                page_size=100
            )

            if not data:
                break

            reviews = data.get("results", [])
            if not reviews:
                break

            all_reviews.extend(reviews)
            self.logger.info(f"采集评价数据第{page}页，累计: {len(all_reviews)} 条评价")

            if not data.get("next"):
                break

            page += 1

        self.stats.total_reviews = len(all_reviews)
        self.logger.info(f"评价数据采集完成，总计: {len(all_reviews)} 条评价")
        return all_reviews

    def _collect_course_details(self, course_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """并行采集课程详情"""
        self.logger.info(f"开始采集 {len(course_ids)} 门课程的详细信息...")
        course_details = {}

        def fetch_course_detail(course_id: int) -> Tuple[int, Optional[Dict[str, Any]]]:
            try:
                if self.client is None:
                    return course_id, None

                detail = self._make_request_with_retry(
                    self.client.get_course_detail,
                    course_id
                )
                return course_id, detail
            except Exception as e:
                self.logger.error(f"获取课程 {course_id} 详情失败: {e}")
                return course_id, None

        # 使用线程池并行获取
        with ThreadPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            future_to_id = {
                executor.submit(fetch_course_detail, course_id): course_id
                for course_id in course_ids
            }

            completed = 0
            for future in as_completed(future_to_id):
                course_id, detail = future.result()
                if detail:
                    course_details[course_id] = detail

                completed += 1
                if completed % 10 == 0:
                    self.logger.info(f"课程详情采集进度: {completed}/{len(course_ids)}")

        self.logger.info(f"课程详情采集完成: {len(course_details)}/{len(course_ids)}")
        return course_details

    def _collect_course_reviews(self, course_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        """并行采集课程评价"""
        self.logger.info(f"开始采集 {len(course_ids)} 门课程的评价...")
        course_reviews = {}

        def fetch_course_reviews(course_id: int) -> Tuple[int, List[Dict[str, Any]]]:
            try:
                if self.client is None:
                    return course_id, []

                all_reviews = []
                page = 1

                while True:
                    data = self._make_request_with_retry(
                        self.client.get_course_reviews,
                        course_id,
                        page=page,
                        page_size=100
                    )

                    if not data:
                        break

                    reviews = data.get("results", [])
                    if not reviews:
                        break

                    all_reviews.extend(reviews)

                    if not data.get("next"):
                        break

                    page += 1

                return course_id, all_reviews

            except Exception as e:
                self.logger.error(f"获取课程 {course_id} 评价失败: {e}")
                return course_id, []

        # 使用线程池并行获取
        with ThreadPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            future_to_id = {
                executor.submit(fetch_course_reviews, course_id): course_id
                for course_id in course_ids
            }

            completed = 0
            for future in as_completed(future_to_id):
                course_id, reviews = future.result()
                if reviews:
                    course_reviews[course_id] = reviews

                completed += 1
                if completed % 10 == 0:
                    self.logger.info(f"课程评价采集进度: {completed}/{len(course_ids)}")

        self.logger.info(f"课程评价采集完成: {len(course_reviews)} 门课程")
        return course_reviews

    def _collect_metadata(self) -> Dict[str, Any]:
        """收集元数据"""
        self.logger.info("收集元数据...")
        metadata = {}

        if self.client is None:
            self.logger.error("API客户端未初始化")
            return metadata

        # 统计信息
        stats = self._make_request_with_retry(self.client.get_statistics)
        if stats:
            metadata["statistics"] = stats

        # 筛选选项
        filter_options = self._make_request_with_retry(self.client.get_course_filter_options)
        if filter_options:
            metadata["filter_options"] = filter_options

        # 学期信息
        semesters = self._make_request_with_retry(self.client.get_semesters)
        if semesters:
            metadata["semesters"] = semesters

        # 通用信息
        common_info = self._make_request_with_retry(self.client.get_common_info)
        if common_info:
            metadata["common_info"] = common_info

        return metadata

    def _determine_courses_to_update(self, courses: List[Dict[str, Any]]) -> List[int]:
        """确定需要更新的课程ID"""
        if self.config.force_full_sync or not self.config.incremental_update:
            return [course["id"] for course in courses]

        courses_to_update = []
        existing_courses = self.existing_data.get("courses_index", {}).get("courses", [])
        existing_course_map = {c["id"]: c for c in existing_courses}

        for course in courses:
            course_id = course["id"]

            # 新课程
            if course_id not in existing_course_map:
                courses_to_update.append(course_id)
                self.stats.new_courses += 1
                continue

            # 检查是否有更新
            existing_course = existing_course_map[course_id]

            # 简单的比较，可以基于评价数量或时间戳
            if (course.get("rating", {}).get("count", 0) !=
                existing_course.get("rating", {}).get("count", 0)):
                courses_to_update.append(course_id)
                self.stats.updated_courses += 1

        self.logger.info(f"增量更新: 新课程 {self.stats.new_courses} 门, 更新课程 {self.stats.updated_courses} 门")
        return courses_to_update

    def _save_courses_data(self, courses: List[Dict[str, Any]], course_details: Dict[int, Dict[str, Any]]):
        """保存课程数据"""
        self.logger.info("保存课程数据...")

        # 课程索引
        courses_index = {
            "total": len(courses),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "courses": courses
        }

        # 保存课程索引
        index_file = self.config.data_dir / "courses" / "index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(courses_index, f, ensure_ascii=False, indent=2)

        # 保存课程详情
        for course_id, detail in course_details.items():
            detail_file = self.config.data_dir / "courses" / "details" / f"{course_id}.json"
            with open(detail_file, 'w', encoding='utf-8') as f:
                json.dump(detail, f, ensure_ascii=False, indent=2)

        # 按院系分类
        departments = {}
        for course in courses:
            dept = course.get("department", "未知院系")
            if dept not in departments:
                departments[dept] = []
            departments[dept].append(course)

        for dept, dept_courses in departments.items():
            dept_file = self.config.data_dir / "courses" / "by-department" / f"{dept}.json"
            with open(dept_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "department": dept,
                    "total": len(dept_courses),
                    "courses": dept_courses
                }, f, ensure_ascii=False, indent=2)

        # 按类别分类
        categories = {}
        for course in courses:
            for category in course.get("categories", []):
                if category not in categories:
                    categories[category] = []
                categories[category].append(course)

        for category, cat_courses in categories.items():
            cat_file = self.config.data_dir / "courses" / "by-category" / f"{category}.json"
            with open(cat_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "category": category,
                    "total": len(cat_courses),
                    "courses": cat_courses
                }, f, ensure_ascii=False, indent=2)

        self.logger.info(f"课程数据保存完成: {len(courses)} 门课程, {len(course_details)} 个详情")

    def _save_reviews_data(self, reviews: List[Dict[str, Any]], course_reviews: Dict[int, List[Dict[str, Any]]]):
        """保存评价数据"""
        self.logger.info("保存评价数据...")

        # 评价索引
        reviews_index = {
            "total": len(reviews),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "reviews": reviews[:1000]  # 只保存最新的1000条在索引中
        }

        # 保存评价索引
        index_file = self.config.data_dir / "reviews" / "index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(reviews_index, f, ensure_ascii=False, indent=2)

        # 按课程保存评价
        for course_id, course_review_list in course_reviews.items():
            reviews_file = self.config.data_dir / "reviews" / "by-course" / f"{course_id}.json"
            with open(reviews_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "course_id": course_id,
                    "total": len(course_review_list),
                    "reviews": course_review_list
                }, f, ensure_ascii=False, indent=2)

        # 最新评价
        latest_reviews = sorted(reviews, key=lambda x: x.get("created_at", ""), reverse=True)[:100]
        latest_file = self.config.data_dir / "reviews" / "latest" / "latest.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump({
                "total": len(latest_reviews),
                "reviews": latest_reviews
            }, f, ensure_ascii=False, indent=2)

        self.logger.info(f"评价数据保存完成: {len(reviews)} 条评价, {len(course_reviews)} 门课程的评价")

    def _save_metadata(self, metadata: Dict[str, Any]):
        """保存元数据"""
        self.logger.info("保存元数据...")

        # 统计信息
        if "statistics" in metadata:
            stats_file = self.config.data_dir / "statistics" / "summary.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(metadata["statistics"], f, ensure_ascii=False, indent=2)

        # 筛选选项
        if "filter_options" in metadata:
            filter_options = metadata["filter_options"]

            # 院系
            if "departments" in filter_options:
                dept_file = self.config.data_dir / "filters" / "departments.json"
                with open(dept_file, 'w', encoding='utf-8') as f:
                    json.dump(filter_options["departments"], f, ensure_ascii=False, indent=2)

            # 类别
            if "categories" in filter_options:
                cat_file = self.config.data_dir / "filters" / "categories.json"
                with open(cat_file, 'w', encoding='utf-8') as f:
                    json.dump(filter_options["categories"], f, ensure_ascii=False, indent=2)

        # 学期
        if "semesters" in metadata:
            sem_file = self.config.data_dir / "filters" / "semesters.json"
            with open(sem_file, 'w', encoding='utf-8') as f:
                json.dump(metadata["semesters"], f, ensure_ascii=False, indent=2)

        # 同步元数据 - 处理datetime对象
        stats_dict = asdict(self.stats)
        # 转换datetime对象为ISO格式字符串
        if stats_dict.get('start_time'):
            stats_dict['start_time'] = stats_dict['start_time'].isoformat()
        if stats_dict.get('end_time'):
            stats_dict['end_time'] = stats_dict['end_time'].isoformat()

        sync_metadata = {
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "sync_stats": stats_dict,
            "config": {
                "incremental_update": self.config.incremental_update,
                "force_full_sync": self.config.force_full_sync,
            }
        }

        metadata_file = self.config.data_dir / "sync_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(sync_metadata, f, ensure_ascii=False, indent=2)

        self.logger.info("元数据保存完成")

    def run_sync(self) -> bool:
        """运行完整同步"""
        try:
            self.logger.info("="*50)
            self.logger.info("开始数据同步")
            self.logger.info("="*50)

            # 初始化客户端
            if not self._init_client():
                self.logger.error("客户端初始化失败")
                return False

            # 1. 收集元数据
            metadata = self._collect_metadata()

            # 2. 采集课程数据
            courses = self._collect_all_courses()
            if not courses:
                self.logger.error("课程数据采集失败")
                return False

            # 3. 确定需要更新的课程
            courses_to_update = self._determine_courses_to_update(courses)

            # 4. 采集课程详情
            course_details = {}
            if courses_to_update:
                course_details = self._collect_course_details(courses_to_update)

            # 5. 采集所有评价
            reviews = self._collect_all_reviews()

            # 6. 采集课程评价
            course_reviews = {}
            if courses_to_update:
                course_reviews = self._collect_course_reviews(courses_to_update)

            # 7. 保存数据
            self._save_courses_data(courses, course_details)
            self._save_reviews_data(reviews, course_reviews)
            self._save_metadata(metadata)

            # 8. 更新统计
            self.stats.end_time = datetime.now(timezone.utc)

            self.logger.info("="*50)
            self.logger.info("数据同步完成")
            self.logger.info(f"总课程数: {self.stats.total_courses}")
            self.logger.info(f"总评价数: {self.stats.total_reviews}")
            self.logger.info(f"新增课程: {self.stats.new_courses}")
            self.logger.info(f"更新课程: {self.stats.updated_courses}")
            self.logger.info(f"API请求数: {self.stats.api_requests}")
            self.logger.info(f"失败请求数: {self.stats.failed_requests}")
            self.logger.info(f"耗时: {(self.stats.end_time - self.stats.start_time).total_seconds():.2f}秒")
            self.logger.info("="*50)

            return True

        except Exception as e:
            self.logger.error(f"同步过程出现异常: {e}")
            self.logger.error(traceback.format_exc())
            self.stats.errors.append(f"同步异常: {e}")
            return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="tongji.icu 镜像站数据同步")
    parser.add_argument("--cookie", help="Cookie字符串")
    parser.add_argument("--output-dir", default="docs", help="输出目录")
    parser.add_argument("--max-pages", type=int, help="每个端点最大页数（用于测试）")
    parser.add_argument("--force-full", action="store_true", help="强制完整同步")
    parser.add_argument("--no-incremental", action="store_true", help="禁用增量更新")
    parser.add_argument("--parallel-workers", type=int, default=4, help="并行工作线程数")

    args = parser.parse_args()

    # 配置
    config = SyncConfig(
        output_dir=Path(args.output_dir),
        data_dir=Path(args.output_dir) / "data",
        max_pages_per_endpoint=args.max_pages,
        force_full_sync=args.force_full,
        incremental_update=not args.no_incremental,
        parallel_workers=args.parallel_workers
    )

    # Cookie
    cookie_string = args.cookie
    if not cookie_string and os.path.exists("cookies.ini"):
        with open("cookies.ini", "r", encoding="utf-8") as f:
            lines = f.readlines()
        cookie_string = "; ".join(line.strip() for line in lines)

    # 运行同步
    syncer = MirrorSiteSyncer(config, cookie_string)
    success = syncer.run_sync()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()